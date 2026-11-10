"""FastAPI routes for login, refresh, logout, and the current-user lookup."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from netvault.auth.deps import get_current_user
from netvault.auth.schemas import LoginRequest, LoginResponse, UserPublic
from netvault.auth.service import (
    AccountLockedError,
    InvalidCredentialsError,
    authenticate,
    logout,
    refresh,
)
from netvault.config import Settings
from netvault.deps import get_session, get_settings
from netvault.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "netvault_refresh"
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.demo_mode,
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
        max_age=settings.refresh_token_ttl_seconds,
    )


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    try:
        result = await authenticate(
            db,
            settings,
            tenant_slug=body.tenant_slug,
            email=body.email,
            password=body.password,
        )
    except AccountLockedError as exc:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "code": "account_locked",
                "message": "Account is temporarily locked after repeated failures",
                "locked_until": exc.locked_until.isoformat(),
                "remediation": "Wait for the lockout window to pass or ask an administrator",
            },
        ) from None
    except InvalidCredentialsError:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credentials",
                "message": "Email or password is incorrect",
            },
        ) from None

    await db.commit()
    _set_refresh_cookie(response, result.refresh_token, settings)
    return LoginResponse(
        access_token=result.access_token,
        access_expires_at=result.access_expires_at,
        user=UserPublic.model_validate(result.user),
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_endpoint(
    response: Response,
    netvault_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    if not netvault_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_refresh"},
        )
    try:
        result = await refresh(db, settings, netvault_refresh)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_refresh"},
        ) from None

    await db.commit()
    _set_refresh_cookie(response, result.refresh_token, settings)
    return LoginResponse(
        access_token=result.access_token,
        access_expires_at=result.access_expires_at,
        user=UserPublic.model_validate(result.user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    response: Response,
    netvault_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_session),
) -> Response:
    if netvault_refresh:
        await logout(db, netvault_refresh)
        await db.commit()
    response.delete_cookie(REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserPublic)
async def me_endpoint(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)
