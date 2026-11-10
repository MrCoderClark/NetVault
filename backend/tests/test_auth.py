from collections.abc import AsyncIterator
from datetime import timedelta
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from netvault.auth.api import REFRESH_COOKIE_NAME
from netvault.config import Settings
from netvault.main import create_app
from netvault.models import Base
from netvault.models import Session as SessionRow
from netvault.models import User, utcnow
from netvault.seed import DEMO_EMAIL, DEMO_PASSWORD_FALLBACK, seed_demo


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    db = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with db.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield db
    finally:
        await db.dispose()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret="x" * 48,
        max_failed_logins=3,
        lockout_duration_seconds=60,
    )


def _login_body(**overrides: str) -> dict[str, str]:
    body = {
        "tenant_slug": "demo",
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD_FALLBACK,
    }
    body.update(overrides)
    return body


async def _client(
    engine: AsyncEngine, settings: Settings
) -> tuple[AsyncClient, object]:
    app = create_app(settings, engine)
    context = app.router.lifespan_context(app)
    await context.__aenter__()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, context


@pytest.mark.asyncio
async def test_login_succeeds_and_refresh_cookie_set(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        response = await client.post("/api/v1/auth/login", json=_login_body())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["access_token"]
        assert body["user"]["email"] == DEMO_EMAIL
        assert REFRESH_COOKIE_NAME in response.cookies
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        response = await client.post(
            "/api/v1/auth/login", json=_login_body(password="nope")
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "invalid_credentials"
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_login_rejects_unknown_tenant_without_leaking(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        response = await client.post(
            "/api/v1/auth/login", json=_login_body(tenant_slug="missing")
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "invalid_credentials"
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_lockout_after_consecutive_failures(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        for _ in range(settings.max_failed_logins):
            bad = await client.post(
                "/api/v1/auth/login", json=_login_body(password="wrong")
            )
            assert bad.status_code == 401
        locked = await client.post(
            "/api/v1/auth/login", json=_login_body(password=DEMO_PASSWORD_FALLBACK)
        )
        assert locked.status_code == 423
        assert locked.json()["detail"]["code"] == "account_locked"
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_me_requires_access_token(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        anon = await client.get("/api/v1/auth/me")
        assert anon.status_code == 401
        assert anon.json()["detail"]["code"] == "missing_token"

        login = await client.post("/api/v1/auth/login", json=_login_body())
        token = login.json()["access_token"]
        me = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me.status_code == 200
        assert me.json()["email"] == DEMO_EMAIL

        bad = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer tampered"}
        )
        assert bad.status_code == 401
        assert bad.json()["detail"]["code"] == "invalid_token"
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_logout_revokes(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        login = await client.post("/api/v1/auth/login", json=_login_body())
        first_cookie = login.cookies.get(REFRESH_COOKIE_NAME)
        assert first_cookie

        refreshed = await client.post("/api/v1/auth/refresh")
        assert refreshed.status_code == 200
        second_cookie = refreshed.cookies.get(REFRESH_COOKIE_NAME)
        assert second_cookie and second_cookie != first_cookie

        # Old cookie is useless now because refresh rotated it.
        client.cookies.clear()
        client.cookies.set(REFRESH_COOKIE_NAME, first_cookie, path="/api/v1/auth")
        stale = await client.post("/api/v1/auth/refresh")
        assert stale.status_code == 401

        # Logout with the live cookie revokes the session row.
        client.cookies.clear()
        client.cookies.set(REFRESH_COOKIE_NAME, second_cookie, path="/api/v1/auth")
        logout = await client.post("/api/v1/auth/logout")
        assert logout.status_code == 204

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            rows = (await db.scalars(select(SessionRow))).all()
            assert rows and all(row.revoked_at is not None for row in rows)
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_me_rejects_expired_session(
    engine: AsyncEngine, settings: Settings
) -> None:
    await seed_demo(engine)
    client, context = await _client(engine, settings)
    try:
        login = await client.post("/api/v1/auth/login", json=_login_body())
        token = login.json()["access_token"]

        # Force the session to look expired by moving its idle window into the past.
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            user = cast(
                User, await db.scalar(select(User).where(User.email == DEMO_EMAIL))
            )
            row = cast(
                SessionRow,
                await db.scalar(select(SessionRow).where(SessionRow.user_id == user.id)),
            )
            row.idle_expires_at = utcnow() - timedelta(hours=1)
            await db.commit()

        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "session_revoked"
    finally:
        await client.aclose()
        await context.__aexit__(None, None, None)
