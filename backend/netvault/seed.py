import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from netvault.config import Settings
from netvault.models import DemoActivity, Host, Tenant


async def seed_demo(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.slug == "demo"))
        if tenant is None:
            tenant = Tenant(slug="demo", name="Example tenant")
            session.add(tenant)
            await session.flush()

        existing = await session.scalar(select(Host.id).where(Host.tenant_id == tenant.id).limit(1))
        if existing is not None:
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
