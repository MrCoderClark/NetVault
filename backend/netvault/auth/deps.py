"""FastAPI dependency that resolves the current authenticated user and permissions."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netvault.config import Settings
from netvault.deps import get_session, get_settings
from netvault.models import User
from netvault.security.rbac import user_has_permission
from netvault.security.sessions import find_active_session_by_id
from netvault.security.tokens import decode_access_token


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("missing_token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise _unauthorized("missing_token")

    try:
        payload = decode_access_token(settings, token)
    except PyJWTError:
        raise _unauthorized("invalid_token") from None

    user_id = payload.get("sub")
    session_id = payload.get("sid")
    tenant_id = payload.get("tenant")
    if not user_id or not session_id or not tenant_id:
        raise _unauthorized("invalid_token")

    row = await find_active_session_by_id(db, session_id)
    if row is None or row.user_id != user_id or row.tenant_id != tenant_id:
        raise _unauthorized("session_revoked")

    user = await db.scalar(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    if user is None:
        raise _unauthorized("user_disabled")

    return user


def require_permission(
    permission_name: str,
) -> Callable[[User, AsyncSession], Coroutine[Any, Any, User]]:
    """Return a FastAPI dependency that enforces the named permission."""

    async def dependency(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> User:
        if not await user_has_permission(
            db, user_id=user.id, permission_name=permission_name
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "forbidden",
                    "required_permission": permission_name,
                },
            )
        return user

    return dependency
