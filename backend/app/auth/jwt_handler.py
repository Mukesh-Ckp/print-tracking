"""JWT token creation and decoding helpers (HS256)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from ..config import settings


def create_access_token(
    subject: str | int,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    subject:
        Value placed in the standard ``sub`` claim (typically the admin id).
    extra_claims:
        Additional claims to merge into the token payload.
    expires_minutes:
        Override the default expiry (defaults to ``settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES``).
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify an access token. Raises ``JWTError`` on any failure.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


__all__ = ["create_access_token", "decode_access_token", "JWTError"]
