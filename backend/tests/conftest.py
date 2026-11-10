from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from netvault.config import Settings
from netvault.main import create_app
from netvault.models import Base


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
def test_settings() -> Settings:
    return Settings(
        jwt_secret="x" * 48,
        max_failed_logins=3,
        lockout_duration_seconds=60,
    )


@pytest.fixture
async def client(
    engine: AsyncEngine, test_settings: Settings
) -> AsyncIterator[AsyncClient]:
    app = create_app(test_settings, engine)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client


async def login(
    client: AsyncClient,
    email: str,
    password: str,
    tenant_slug: str = "demo",
) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": tenant_slug, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
