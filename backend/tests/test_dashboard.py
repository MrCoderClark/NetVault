import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from netvault.config import Settings
from netvault.seed import DEMO_EMAIL, DEMO_PASSWORD_FALLBACK, seed_demo
from tests.conftest import bearer, login


@pytest.mark.asyncio
async def test_demo_seed_is_idempotent_and_serves_dashboard(
    engine: AsyncEngine, client: AsyncClient
) -> None:
    await seed_demo(engine)
    await seed_demo(engine)
    token = await login(client, DEMO_EMAIL, DEMO_PASSWORD_FALLBACK)

    response = await client.get("/api/v1/dashboard", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["demo_mode"] is True
    assert body["tenant_name"] == "Example tenant"
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
async def test_dashboard_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "missing_token"


@pytest.mark.asyncio
async def test_dashboard_site_filter_and_validation(
    engine: AsyncEngine, client: AsyncClient
) -> None:
    await seed_demo(engine)
    token = await login(client, DEMO_EMAIL, DEMO_PASSWORD_FALLBACK)
    headers = bearer(token)

    other = await client.get("/api/v1/dashboard?site=other-site", headers=headers)
    assert other.status_code == 200
    assert other.json()["stats"]["hosts"] == 0
    assert other.json()["activities"] == []

    invalid = await client.get("/api/v1/dashboard?site=../../etc", headers=headers)
    assert invalid.status_code == 422


def test_non_demo_mode_requires_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET must be set"):
        Settings(demo_mode=False)


def test_demo_mode_generates_ephemeral_jwt_secret() -> None:
    assert len(Settings(demo_mode=True).jwt_secret) >= 32
