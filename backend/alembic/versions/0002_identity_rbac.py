"""Identity, RBAC, audit chain, and credential metadata schema.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "permission",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("resource", sa.String(80), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )
    op.create_index("ix_user_tenant", "user", ["tenant_id"])

    op.create_table(
        "role",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("role.id"), primary_key=True),
        sa.Column(
            "permission_id", sa.String(36), sa.ForeignKey("permission.id"), primary_key=True
        ),
    )

    op.create_table(
        "user_role",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("role.id"), nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("scope_kind", sa.String(40), nullable=True),
        sa.Column("scope_value", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_role_tenant_user", "user_role", ["tenant_id", "user_id"])

    op.create_table(
        "session",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("refresh_hash", sa.String(128), nullable=False),
        sa.Column("device_label", sa.String(120), nullable=False, server_default=""),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_tenant_user", "session", ["tenant_id", "user_id"])
    op.create_index("ix_session_refresh_hash", "session", ["refresh_hash"])

    op.create_table(
        "api_key",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("principal_user_id", sa.String(36), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("principal_name", sa.String(120), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_api_key_tenant", "api_key", ["tenant_id"])
    op.create_index("ix_api_key_key_hash", "api_key", ["key_hash"])

    op.create_table(
        "audit_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("tenant_seq", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.String(80), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=True),
        sa.Column("target_id", sa.String(80), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("correlation_id", sa.String(80), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("tenant_id", "tenant_seq", name="uq_audit_tenant_seq"),
    )
    op.create_index("ix_audit_tenant_occurred", "audit_event", ["tenant_id", "occurred_at"])

    op.create_table(
        "credential",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("username", sa.String(160), nullable=False),
        sa.Column("domain", sa.String(160), nullable=True),
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
        sa.Column("rotation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_credential_tenant_name"),
    )

    op.create_table(
        "credential_scope",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "credential_id", sa.String(36), sa.ForeignKey("credential.id"), nullable=False
        ),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("scope_kind", sa.String(40), nullable=False),
        sa.Column("scope_value", sa.String(300), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credential_scope_credential", "credential_scope", ["credential_id"])

    op.create_table(
        "secret_ref",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "credential_id", sa.String(36), sa.ForeignKey("credential.id"), nullable=False
        ),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("backend", sa.String(40), nullable=False),
        sa.Column("locator", sa.String(500), nullable=False),
        sa.Column("version_metadata", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_secret_ref_credential", "secret_ref", ["credential_id"])


def downgrade() -> None:
    op.drop_index("ix_secret_ref_credential", table_name="secret_ref")
    op.drop_table("secret_ref")
    op.drop_index("ix_credential_scope_credential", table_name="credential_scope")
    op.drop_table("credential_scope")
    op.drop_table("credential")
    op.drop_index("ix_audit_tenant_occurred", table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_index("ix_api_key_key_hash", table_name="api_key")
    op.drop_index("ix_api_key_tenant", table_name="api_key")
    op.drop_table("api_key")
    op.drop_index("ix_session_refresh_hash", table_name="session")
    op.drop_index("ix_session_tenant_user", table_name="session")
    op.drop_table("session")
    op.drop_index("ix_user_role_tenant_user", table_name="user_role")
    op.drop_table("user_role")
    op.drop_table("role_permission")
    op.drop_table("role")
    op.drop_index("ix_user_tenant", table_name="user")
    op.drop_table("user")
    op.drop_table("permission")
