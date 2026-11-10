from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from netvault.config import Settings
from netvault.main import create_app
from netvault.models import Base
from netvault.seed import seed_demo


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    db = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with db.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield db
    finally:
        await db.dispose()


@pytest.mark.asyncio
async def test_demo_seed_is_idempotent(engine: AsyncEngine) -> None:
    await seed_demo(engine)
    await seed_demo(engine)
    app = create_app(Settings(), engine)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/dashboard")
            assert response.status_code == 200
            body = response.json()
            assert body["demo_mode"] is True
            assert body["stats"] == {
                "hosts": 6,
                "protected_bytes": 0,
                "success_24h_percent": None,
                "critical": 0,
                "running_jobs": 0,
            }
            assert len(body["activities"]) == 6
            assert all(host["status"] == "unknown" for host in body["hosts"])
            assert all(row["label"] == "Example only" for row in body["activities"])
            assert (await client.get("/healthz")).json() == {"status": "ok"}
            assert (await client.get("/readyz")).json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_site_filter_and_unseeded_error(engine: AsyncEngine) -> None:
    app = create_app(Settings(), engine)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/v1/dashboard")).status_code == 503
            await seed_demo(engine)
            response = await client.get("/api/v1/dashboard?site=other-site")
            assert response.status_code == 200
            assert response.json()["stats"]["hosts"] == 0
            assert response.json()["activities"] == []
            assert (await client.get("/api/v1/dashboard?site=../../etc")).status_code == 422


def test_non_demo_mode_requires_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET must be set"):
        Settings(demo_mode=False)


def test_demo_mode_generates_ephemeral_jwt_secret() -> None:
    assert len(Settings(demo_mode=True).jwt_secret) >= 32
