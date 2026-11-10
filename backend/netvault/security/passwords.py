"""Argon2id password hashing.

Hashes are never logged, returned in API responses, or included in audit
payloads. The hasher parameters below are a reasonable starting point and
should be tuned for the production worker's CPU/memory profile with a
measured login-latency budget before go-live.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
)


def hash_password(password: str) -> str:
    """Return an Argon2id hash. Rejects empty passwords; callers enforce length policy."""
    if not password:
        raise ValueError("Password must not be empty")
    return _hasher.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    """Return True only if the password matches the stored hash.

    All exceptions from the hasher collapse to False so callers never leak a
    reason via timing or control flow.
    """
    if not hashed or not password:
        return False
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Return True if the stored hash was produced with weaker parameters than the current policy."""
    return _hasher.check_needs_rehash(hashed)
