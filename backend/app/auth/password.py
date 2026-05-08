"""Password hashing utilities backed by bcrypt (via passlib)."""

from __future__ import annotations

from passlib.context import CryptContext

# bcrypt is the de-facto standard for password hashing in Python web apps.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of *plain_password*."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches the stored bcrypt *hashed_password*."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Defensive: never let a malformed hash crash the auth flow.
        return False
