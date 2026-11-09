"""Create the demo-only foundation schema.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
    )
    op.create_table(
        "host",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("site", sa.String(80), nullable=False),
        sa.Column("reachability", sa.String(20), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_host_tenant_site", "host", ["tenant_id", "site"])
    op.create_table(
        "demo_activity",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("site", sa.String(80), nullable=False),
        sa.Column("host_name", sa.String(120), nullable=False),
        sa.Column("target_name", sa.String(120), nullable=False),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_demo_activity_tenant_site_occurred",
        "demo_activity",
        ["tenant_id", "site", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_demo_activity_tenant_site_occurred", table_name="demo_activity")
    op.drop_table("demo_activity")
    op.drop_index("ix_host_tenant_site", table_name="host")
    op.drop_table("host")
    op.drop_table("tenant")
