from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netvault.models import DemoActivity, Host, Tenant
from netvault.schemas import Activity, Dashboard, Reachability, Stats


async def load_dashboard(session: AsyncSession, site: str) -> Dashboard:
    tenant = await session.scalar(select(Tenant).where(Tenant.slug == "demo"))
    if tenant is None:
        raise RuntimeError("Demo data is missing. Run the seed command first.")

    hosts = (
        await session.scalars(
            select(Host)
            .where(Host.tenant_id == tenant.id, Host.site == site, Host.is_demo.is_(True))
            .order_by(Host.name)
        )
    ).all()
    activities = (
        await session.scalars(
            select(DemoActivity)
            .where(DemoActivity.tenant_id == tenant.id, DemoActivity.site == site)
            .order_by(DemoActivity.occurred_at.desc())
            .limit(16)
        )
    ).all()
    return Dashboard(
        demo_mode=True,
        tenant_name=tenant.name,
        site=site,
        stats=Stats(
            hosts=len(hosts),
            protected_bytes=0,
            success_24h_percent=None,
            critical=0,
            running_jobs=0,
        ),
        activities=[Activity.model_validate(activity) for activity in activities],
        hosts=[Reachability(name=host.name, status=host.reachability, sample=True) for host in hosts],
        read_mbps=[],
        write_mbps=[],
    )
