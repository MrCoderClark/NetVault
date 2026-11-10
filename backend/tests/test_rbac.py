import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from netvault.models import DemoActivity, Host, Tenant, User
from netvault.security.passwords import hash_password
from netvault.security.rbac import (
    ALL_PERMISSIONS,
    SYSTEM_ROLES,
    ensure_user_role,
    seed_permission_catalogue,
    seed_system_roles,
    user_has_permission,
)
from netvault.seed import DEMO_EMAIL, DEMO_PASSWORD_FALLBACK, seed_demo
from tests.conftest import bearer, login


async def _create_tenant_with_user(
    engine: AsyncEngine,
    *,
    slug: str,
    email: str,
    password: str,
    role_name: str | None,
    host_name: str,
    site: str = "eu-dublin",
) -> None:
    """Create a tenant, user, optional role, and one demo host/activity."""
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        async with db.begin():
            tenant = Tenant(slug=slug, name=f"Tenant {slug}")
            db.add(tenant)
            await db.flush()

            permission_ids = await seed_permission_catalogue(db)
            role_ids = await seed_system_roles(db, tenant.id, permission_ids)

            user = User(
                tenant_id=tenant.id,
                email=email,
                display_name=email,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            await db.flush()

            if role_name is not None:
                await ensure_user_role(
                    db,
                    user_id=user.id,
                    role_id=role_ids[role_name],
                    tenant_id=tenant.id,
                )

            db.add(
                Host(tenant_id=tenant.id, site=site, name=host_name, reachability="unknown")
            )
            db.add(
                DemoActivity(
                    tenant_id=tenant.id,
                    site=site,
                    host_name=host_name,
                    target_name="demo",
                    job_type="FULL",
                    progress=50,
                )
            )


@pytest.mark.asyncio
async def test_dashboard_requires_dashboard_read_permission(
    engine: AsyncEngine, client: AsyncClient
) -> None:
    await _create_tenant_with_user(
        engine,
        slug="demo",
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD_FALLBACK,
        role_name=None,  # no role assigned
        host_name="HOST-A",
    )
    token = await login(client, DEMO_EMAIL, DEMO_PASSWORD_FALLBACK)
    response = await client.get("/api/v1/dashboard", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["detail"]["required_permission"] == "dashboard:read"


@pytest.mark.asyncio
async def test_viewer_role_can_read_dashboard(
    engine: AsyncEngine, client: AsyncClient
) -> None:
    await _create_tenant_with_user(
        engine,
        slug="demo",
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD_FALLBACK,
        role_name="Viewer",
        host_name="HOST-A",
    )
    token = await login(client, DEMO_EMAIL, DEMO_PASSWORD_FALLBACK)
    response = await client.get("/api/v1/dashboard", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["stats"]["hosts"] == 1


@pytest.mark.asyncio
async def test_dashboard_excludes_other_tenant_rows(
    engine: AsyncEngine, client: AsyncClient
) -> None:
    await _create_tenant_with_user(
        engine,
        slug="demo",
        email="alpha@example.com",
        password="password-alpha",
        role_name="SuperAdmin",
        host_name="HOST-ALPHA",
    )
    await _create_tenant_with_user(
        engine,
        slug="beta",
        email="beta@example.com",
        password="password-beta",
        role_name="SuperAdmin",
        host_name="HOST-BETA",
    )

    alpha_token = await login(
        client, "alpha@example.com", "password-alpha", tenant_slug="demo"
    )
    alpha = await client.get("/api/v1/dashboard", headers=bearer(alpha_token))
    assert alpha.status_code == 200
    alpha_body = alpha.json()
    assert alpha_body["tenant_name"] == "Tenant demo"
    assert {host["name"] for host in alpha_body["hosts"]} == {"HOST-ALPHA"}

    beta_token = await login(
        client, "beta@example.com", "password-beta", tenant_slug="beta"
    )
    beta = await client.get("/api/v1/dashboard", headers=bearer(beta_token))
    assert beta.status_code == 200
    beta_body = beta.json()
    assert beta_body["tenant_name"] == "Tenant beta"
    assert {host["name"] for host in beta_body["hosts"]} == {"HOST-BETA"}


@pytest.mark.asyncio
async def test_permission_matrix_matches_role_definitions(engine: AsyncEngine) -> None:
    """Verify each system role resolves to exactly the permissions it declares."""
    await seed_demo(engine)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        tenant = await db.scalar(select(Tenant).where(Tenant.slug == "demo"))
        assert tenant is not None

        permission_ids = await seed_permission_catalogue(db)
        role_ids = await seed_system_roles(db, tenant.id, permission_ids)

        for defn in SYSTEM_ROLES:
            scratch_email = f"probe-{defn.name.lower()}@example.com"
            probe = User(
                tenant_id=tenant.id,
                email=scratch_email,
                display_name=defn.name,
                password_hash=hash_password("probe-password"),
                is_active=True,
            )
            db.add(probe)
            await db.flush()
            await ensure_user_role(
                db,
                user_id=probe.id,
                role_id=role_ids[defn.name],
                tenant_id=tenant.id,
            )
            await db.commit()

            declared = set(defn.permissions)
            for permission_name in ALL_PERMISSIONS:
                expected = permission_name in declared
                actual = await user_has_permission(
                    db, user_id=probe.id, permission_name=permission_name
                )
                assert actual is expected, (
                    f"Role {defn.name} expected {permission_name}={expected}, got {actual}"
                )


@pytest.mark.asyncio
async def test_unknown_permission_is_denied(engine: AsyncEngine) -> None:
    await seed_demo(engine)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        assert user is not None
        granted = await user_has_permission(
            db, user_id=user.id, permission_name="not:a:real:permission"
        )
        assert granted is False
