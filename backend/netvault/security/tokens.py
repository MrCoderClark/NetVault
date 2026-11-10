"""Access-token (JWT) and refresh-token (opaque) helpers.

Access tokens are short-lived JWTs that the client carries in the
``Authorization: Bearer`` header; they are stateless and expire quickly.
Refresh tokens are long-lived opaque strings stored hashed in the session
table and rotated on every refresh.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from netvault.config import Settings

_ALGORITHM = "HS256"


def generate_refresh_token() -> str:
    """Return a cryptographically random, URL-safe refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hex digest the session row stores."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_access_token(
    settings: Settings,
    *,
    user_id: str,
    tenant_id: str,
    session_id: str,
) -> tuple[str, datetime]:
    """Return ``(token, expires_at)`` for a JWT with the supplied claims."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.access_token_ttl_seconds)
    payload = {
        "sub": user_id,
        "tenant": tenant_id,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)
    return token, expires_at


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    """Return the decoded JWT payload or raise ``jwt.PyJWTError``."""
    payload: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    return payload
