"""Session row lifecycle: create, rotate, revoke, lookup."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netvault.config import Settings
from netvault.models import Session as SessionRow
from netvault.models import User, utcnow
from netvault.security.tokens import generate_refresh_token, hash_refresh_token


async def create_session(
    db: AsyncSession,
    settings: Settings,
    user: User,
    device_label: str = "",
) -> tuple[SessionRow, str]:
    """Insert a new session row for ``user`` and return (row, refresh_token)."""
    now = utcnow()
    refresh_token = generate_refresh_token()
    row = SessionRow(
        tenant_id=user.tenant_id,
        user_id=user.id,
        refresh_hash=hash_refresh_token(refresh_token),
        device_label=device_label,
        idle_expires_at=now + timedelta(seconds=settings.refresh_idle_ttl_seconds),
        absolute_expires_at=now + timedelta(seconds=settings.refresh_token_ttl_seconds),
        created_at=now,
        last_used_at=now,
    )
    db.add(row)
    await db.flush()
    return row, refresh_token


async def rotate_session(
    db: AsyncSession,
    settings: Settings,
    row: SessionRow,
) -> str:
    """Issue a new refresh token, extend idle expiry. Returns the new token."""
    now = utcnow()
    new_token = generate_refresh_token()
    row.refresh_hash = hash_refresh_token(new_token)
    row.idle_expires_at = now + timedelta(seconds=settings.refresh_idle_ttl_seconds)
    row.last_used_at = now
    await db.flush()
    return new_token


async def revoke_session(db: AsyncSession, row: SessionRow) -> None:
    row.revoked_at = utcnow()
    await db.flush()


async def find_active_session_by_refresh(
    db: AsyncSession, refresh_token: str
) -> SessionRow | None:
    hashed = hash_refresh_token(refresh_token)
    now = utcnow()
    return await db.scalar(
        select(SessionRow).where(
            SessionRow.refresh_hash == hashed,
            SessionRow.revoked_at.is_(None),
            SessionRow.idle_expires_at > now,
            SessionRow.absolute_expires_at > now,
        )
    )


async def find_active_session_by_id(db: AsyncSession, session_id: str) -> SessionRow | None:
    now = utcnow()
    return await db.scalar(
        select(SessionRow).where(
            SessionRow.id == session_id,
            SessionRow.revoked_at.is_(None),
            SessionRow.idle_expires_at > now,
            SessionRow.absolute_expires_at > now,
        )
    )
