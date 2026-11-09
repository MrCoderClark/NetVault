from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))

    hosts: Mapped[list["Host"]] = relationship(back_populates="tenant")


class Host(Base):
    __tablename__ = "host"
    __table_args__ = (
        Index("ix_host_tenant_site", "tenant_id", "site"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenant.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120))
    site: Mapped[str] = mapped_column(String(80))
    reachability: Mapped[str] = mapped_column(String(20), default="unknown")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped[Tenant] = relationship(back_populates="hosts")


class DemoActivity(Base):
    __tablename__ = "demo_activity"
    __table_args__ = (
        Index("ix_demo_activity_tenant_site_occurred", "tenant_id", "site", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenant.id"), nullable=False)
    site: Mapped[str] = mapped_column(String(80))
    host_name: Mapped[str] = mapped_column(String(120))
    target_name: Mapped[str] = mapped_column(String(120))
    job_type: Mapped[str] = mapped_column(String(20))
    progress: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
