"""Login, refresh, and logout business logic. No HTTP concerns in this module."""

from __future__ import annotations

import functools
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netvault.config import Settings
from netvault.models import Session as SessionRow
from netvault.models import Tenant, User, ensure_utc, utcnow
from netvault.security.passwords import hash_password, needs_rehash, verify_password
from netvault.security.sessions import (
    create_session,
    find_active_session_by_refresh,
    revoke_session,
    rotate_session,
)
from netvault.security.tokens import issue_access_token


@functools.cache
def _dummy_hash() -> str:
    """Real Argon2id hash used only as a timing decoy on the miss path."""
    return hash_password("timing-decoy-" + secrets.token_urlsafe(24))


class AuthError(Exception):
    """Base for authentication failures the API maps to typed errors."""


class InvalidCredentialsError(AuthError):
    pass


class AccountLockedError(AuthError):
    def __init__(self, locked_until: datetime):
        super().__init__("Account temporarily locked")
        self.locked_until = locked_until


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    session_row: SessionRow
    user: User


async def authenticate(
    db: AsyncSession,
    settings: Settings,
    *,
    tenant_slug: str,
    email: str,
    password: str,
    device_label: str = "",
) -> LoginResult:
    tenant = await db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
    normalized_email = email.strip().lower()

    user: User | None = None
    if tenant is not None:
        user = await db.scalar(
            select(User).where(
                User.tenant_id == tenant.id, User.email == normalized_email
            )
        )

    now = utcnow()
    if user is None or not user.is_active or user.password_hash is None:
        # Spend roughly the same CPU on a miss so the round-trip time is similar.
        verify_password(_dummy_hash(), password)
        raise InvalidCredentialsError()

    locked_until = ensure_utc(user.locked_until)
    if locked_until is not None and locked_until > now:
        raise AccountLockedError(locked_until)

    if not verify_password(user.password_hash, password):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.max_failed_logins:
            user.locked_until = now + timedelta(seconds=settings.lockout_duration_seconds)
        await db.flush()
        raise InvalidCredentialsError()

    user.failed_login_count = 0
    user.locked_until = None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    await db.flush()

    row, refresh_token = await create_session(db, settings, user, device_label)
    access_token, access_expires_at = issue_access_token(
        settings, user_id=user.id, tenant_id=user.tenant_id, session_id=row.id
    )
    return LoginResult(
        access_token=access_token,
        access_expires_at=access_expires_at,
        refresh_token=refresh_token,
        session_row=row,
        user=user,
    )


@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    session_row: SessionRow
    user: User


async def refresh(
    db: AsyncSession,
    settings: Settings,
    refresh_token: str,
) -> RefreshResult:
    row = await find_active_session_by_refresh(db, refresh_token)
    if row is None:
        raise InvalidCredentialsError()
    user = await db.scalar(
        select(User).where(User.id == row.user_id, User.is_active.is_(True))
    )
    if user is None:
        await revoke_session(db, row)
        raise InvalidCredentialsError()

    new_refresh = await rotate_session(db, settings, row)
    access_token, expires_at = issue_access_token(
        settings, user_id=user.id, tenant_id=user.tenant_id, session_id=row.id
    )
    return RefreshResult(
        access_token=access_token,
        access_expires_at=expires_at,
        refresh_token=new_refresh,
        session_row=row,
        user=user,
    )


async def logout(db: AsyncSession, refresh_token: str) -> bool:
    row = await find_active_session_by_refresh(db, refresh_token)
    if row is None:
        return False
    await revoke_session(db, row)
    return True
