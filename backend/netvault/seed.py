import asyncio
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from netvault.config import Settings
from netvault.models import DemoActivity, Host, Tenant, User
from netvault.security.passwords import hash_password

DEMO_EMAIL = "admin@example.com"
DEMO_PASSWORD_ENV = "NETVAULT_DEMO_PASSWORD"
DEMO_PASSWORD_FALLBACK = "demo-change-me"


def _demo_password() -> str:
    value = os.environ.get(DEMO_PASSWORD_ENV, "").strip()
    return value or DEMO_PASSWORD_FALLBACK


async def seed_demo(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.slug == "demo"))
        if tenant is None:
            tenant = Tenant(slug="demo", name="Example tenant")
            session.add(tenant)
            await session.flush()

        existing_user = await session.scalar(
            select(User.id).where(User.tenant_id == tenant.id).limit(1)
        )
        if existing_user is None:
            session.add(
                User(
                    tenant_id=tenant.id,
                    email=DEMO_EMAIL,
                    display_name="Demo Admin",
                    password_hash=hash_password(_demo_password()),
                    is_active=True,
                )
            )

        existing_host = await session.scalar(
            select(Host.id).where(Host.tenant_id == tenant.id).limit(1)
        )
        if existing_host is not None:
            return

        host_names = (
            "WS-PROD-SQL-01",
            "DC-LON-02",
            "SRV-APP-03",
            "SRV-APP-04",
            "SRV-APP-05",
            "DC-LON-06",
        )
        session.add_all(
            Host(tenant_id=tenant.id, site="eu-dublin", name=name, reachability="unknown")
            for name in host_names
        )
        now = datetime.now(timezone.utc)
        session.add_all(
            DemoActivity(
                tenant_id=tenant.id,
                site="eu-dublin",
                host_name=name,
                target_name="Example repository",
                job_type=("FULL", "INCR", "DIFF")[index % 3],
                progress=(34, 62, 100, 14, 77, 41)[index],
                occurred_at=now - timedelta(minutes=index * 13),
            )
            for index, name in enumerate(host_names)
        )


async def main() -> None:
    settings = Settings()
    engine = create_async_engine(settings.database_url())
    try:
        await seed_demo(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
