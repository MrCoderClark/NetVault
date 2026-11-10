"""Permission catalogue, system role definitions, and permission check helpers.

Permissions are a controlled global catalogue of ``resource:action`` names.
Roles are per tenant; built-in system roles are seeded into every tenant on
first boot. Resource-scoped permissions (site/tag/host) are intentionally
not enforced yet; they will be added later without breaking the data model.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netvault.models import Permission, Role, RolePermission, UserRole, utcnow


@dataclass(frozen=True)
class PermissionDef:
    name: str
    resource: str
    action: str
    description: str


PERMISSION_CATALOGUE: tuple[PermissionDef, ...] = (
    PermissionDef("dashboard:read", "dashboard", "read", "View the dashboard"),
    PermissionDef("hosts:read", "hosts", "read", "List hosts and their details"),
    PermissionDef("hosts:write", "hosts", "write", "Create and modify hosts"),
    PermissionDef("hosts:test", "hosts", "test", "Test host connectivity"),
    PermissionDef("credentials:read", "credentials", "read", "List credentials"),
    PermissionDef("credentials:write", "credentials", "write", "Create and modify credentials"),
    PermissionDef("credentials:test", "credentials", "test", "Test credential health"),
    PermissionDef("repositories:read", "repositories", "read", "List repositories"),
    PermissionDef(
        "repositories:write", "repositories", "write", "Create and modify repositories"
    ),
    PermissionDef("repositories:scrub", "repositories", "scrub", "Run repository scrub"),
    PermissionDef("jobs:read", "jobs", "read", "List job templates and instances"),
    PermissionDef("jobs:write", "jobs", "write", "Create and modify job templates"),
    PermissionDef("jobs:trigger", "jobs", "trigger", "Trigger a job template manually"),
    PermissionDef("runs:read", "runs", "read", "View job instance details"),
    PermissionDef("runs:cancel", "runs", "cancel", "Cancel a running job instance"),
    PermissionDef("runs:retry", "runs", "retry", "Retry a failed job instance"),
    PermissionDef("schedules:read", "schedules", "read", "View schedules and previews"),
    PermissionDef("schedules:write", "schedules", "write", "Create and modify schedules"),
    PermissionDef("workflows:read", "workflows", "read", "View workflow definitions"),
    PermissionDef("workflows:write", "workflows", "write", "Create and modify workflows"),
    PermissionDef("workflows:run", "workflows", "run", "Trigger a workflow"),
    PermissionDef("backups:read", "backups", "read", "Browse backup sets"),
    PermissionDef("restores:execute", "restores", "execute", "Request a restore"),
    PermissionDef("reports:read", "reports", "read", "View reports"),
    PermissionDef("reports:export", "reports", "export", "Export reports to CSV or JSON"),
    PermissionDef("audit:read", "audit", "read", "View audit events"),
    PermissionDef("audit:export", "audit", "export", "Export audit events"),
    PermissionDef(
        "notifications:manage",
        "notifications",
        "manage",
        "Manage notification rules and channels",
    ),
    PermissionDef("users:manage", "users", "manage", "Manage users and roles within the tenant"),
    PermissionDef("tenant:manage", "tenant", "manage", "Manage tenant-level settings"),
    PermissionDef("settings:manage", "settings", "manage", "Manage application settings"),
)


ALL_PERMISSIONS: tuple[str, ...] = tuple(p.name for p in PERMISSION_CATALOGUE)
READ_PERMISSIONS: tuple[str, ...] = tuple(
    p.name for p in PERMISSION_CATALOGUE if p.action == "read"
)


@dataclass(frozen=True)
class RoleDef:
    name: str
    description: str
    permissions: tuple[str, ...]


SYSTEM_ROLES: tuple[RoleDef, ...] = (
    RoleDef(
        "Viewer",
        "Read-only access to the fleet, jobs, schedules, and reports",
        READ_PERMISSIONS,
    ),
    RoleDef(
        "Operator",
        "Trigger and retry jobs; test host and credential connectivity",
        READ_PERMISSIONS
        + (
            "hosts:test",
            "credentials:test",
            "jobs:trigger",
            "runs:cancel",
            "runs:retry",
            "workflows:run",
        ),
    ),
    RoleDef(
        "BackupAdmin",
        "Configure hosts, credentials, repositories, schedules, jobs, and workflows",
        READ_PERMISSIONS
        + (
            "hosts:write",
            "hosts:test",
            "credentials:write",
            "credentials:test",
            "repositories:write",
            "repositories:scrub",
            "jobs:write",
            "jobs:trigger",
            "runs:cancel",
            "runs:retry",
            "schedules:write",
            "workflows:write",
            "workflows:run",
            "restores:execute",
            "reports:export",
        ),
    ),
    RoleDef(
        "SecurityAdmin",
        "Manage credentials, users, settings, and audit exports",
        READ_PERMISSIONS
        + (
            "credentials:write",
            "credentials:test",
            "users:manage",
            "settings:manage",
            "notifications:manage",
            "audit:export",
        ),
    ),
    RoleDef(
        "Auditor",
        "Read-only access with audit export",
        READ_PERMISSIONS + ("audit:export", "reports:export"),
    ),
    RoleDef("SuperAdmin", "Full access across every resource", ALL_PERMISSIONS),
)


async def seed_permission_catalogue(db: AsyncSession) -> dict[str, str]:
    """Insert any missing permissions. Returns a ``{name: id}`` map."""
    existing = {p.name: p.id for p in (await db.scalars(select(Permission))).all()}
    for defn in PERMISSION_CATALOGUE:
        if defn.name in existing:
            continue
        row = Permission(
            name=defn.name,
            resource=defn.resource,
            action=defn.action,
            description=defn.description,
        )
        db.add(row)
        await db.flush()
        existing[defn.name] = row.id
    return existing


async def seed_system_roles(
    db: AsyncSession, tenant_id: str, permission_ids: dict[str, str]
) -> dict[str, str]:
    """Create any missing system roles for ``tenant_id`` and link their permissions."""
    existing = {
        r.name: r.id
        for r in (
            await db.scalars(select(Role).where(Role.tenant_id == tenant_id))
        ).all()
    }
    for defn in SYSTEM_ROLES:
        role_id = existing.get(defn.name)
        if role_id is None:
            role = Role(
                tenant_id=tenant_id,
                name=defn.name,
                description=defn.description,
                is_system=True,
            )
            db.add(role)
            await db.flush()
            role_id = role.id
            existing[defn.name] = role_id
        current = {
            rp.permission_id
            for rp in (
                await db.scalars(
                    select(RolePermission).where(RolePermission.role_id == role_id)
                )
            ).all()
        }
        for permission_name in defn.permissions:
            permission_id = permission_ids.get(permission_name)
            if permission_id is None:
                raise RuntimeError(
                    f"Permission {permission_name!r} missing from the catalogue"
                )
            if permission_id in current:
                continue
            db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        await db.flush()
    return existing


async def ensure_user_role(
    db: AsyncSession, *, user_id: str, role_id: str, tenant_id: str
) -> None:
    existing = await db.scalar(
        select(UserRole.id).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
    )
    if existing is None:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=role_id,
                tenant_id=tenant_id,
                created_at=utcnow(),
            )
        )
        await db.flush()


async def user_has_permission(
    db: AsyncSession, *, user_id: str, permission_name: str
) -> bool:
    """Return True when the user has the named permission through any role assignment."""
    row = await db.scalar(
        select(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Permission.name == permission_name)
        .limit(1)
    )
    return row is not None
