"""
FastAPI dependencies for authentication / authorisation.

Two distinct mechanisms are supported:

* Admin JWTs (``Authorization: Bearer <token>``) for the React dashboard.
* A static API key (``X-API-Key: <secret>``) for the on-premise print-agent.
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from ..config import settings
from ..database.session import get_db
from ..models.admin import Admin
from .jwt_handler import decode_access_token

# tokenUrl is informational; the actual login endpoint is /api/auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def get_current_admin(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    """Resolve the admin user attached to the incoming JWT, or raise 401."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        admin_id = payload.get("sub")
        if admin_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    admin = db.query(Admin).filter(Admin.id == int(admin_id)).first()
    if admin is None or not admin.is_active:
        raise credentials_exception
    return admin


def require_agent_api_key(
    # Let FastAPI do the default mapping: `x_api_key` -> `X-API-Key`.
    # (Header names are case-insensitive and underscores map to hyphens.)
    x_api_key: Optional[str] = Header(default=None),
) -> str:
    """
    Validate the print-agent's static API key.

    The header is compared with ``secrets.compare_digest`` to avoid
    timing-attack leakage.
    """
    expected = settings.AGENT_API_KEY
    if not x_api_key or not expected or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )
    return x_api_key
