"""Authentication request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .admin import AdminOut


class LoginRequest(BaseModel):
    """Body for POST /api/auth/login."""

    username: str = Field(..., min_length=1, max_length=128, description="Admin username or email.")
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """JWT response returned by the login endpoint."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token validity in seconds.")
    admin: AdminOut
