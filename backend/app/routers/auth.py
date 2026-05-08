"""Authentication routes: admin login + current-user endpoint."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..auth.jwt_handler import create_access_token
from ..auth.password import verify_password
from ..config import settings
from ..database.session import get_db
from ..models.admin import Admin
from ..schemas.admin import AdminOut
from ..schemas.auth import LoginRequest, TokenResponse
from ..services.activity_service import log_activity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate an admin and obtain a JWT.",
)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    admin: Admin | None = (
        db.query(Admin)
        .filter(or_(Admin.username == payload.username, Admin.email == payload.username))
        .first()
    )
    if not admin or not verify_password(payload.password, admin.hashed_password):
        log_activity(
            db,
            actor=payload.username,
            action="login_failed",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This admin account is disabled.",
        )

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)

    token = create_access_token(subject=admin.id, extra_claims={"username": admin.username})
    log_activity(
        db,
        actor=admin.username,
        action="login_success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin=AdminOut.model_validate(admin),
    )


@router.get("/me", response_model=AdminOut, summary="Current authenticated admin.")
def me(current: Admin = Depends(get_current_admin)) -> AdminOut:
    return AdminOut.model_validate(current)
