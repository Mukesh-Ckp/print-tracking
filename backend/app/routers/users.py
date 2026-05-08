"""User profile and print-limit management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..database.session import get_db
from ..models.admin import Admin
from ..schemas.user_profile import UserProfileOut, UserProfileUpdate, UserSummaryOut
from ..services.print_service import list_user_summaries, upsert_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/summary", response_model=list[UserSummaryOut], summary="List users with print counts and limits.")
def get_user_summary(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
) -> list[UserSummaryOut]:
    rows = list_user_summaries(db)
    return [UserSummaryOut(**row) for row in rows]


@router.put(
    "/{raw_username}",
    response_model=UserProfileOut,
    summary="Create/update a user profile alias and print limit.",
)
def update_user_profile(
    raw_username: str,
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
) -> UserProfileOut:
    if not current.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin privileges required.")

    try:
        profile = upsert_user_profile(
            db,
            raw_username=raw_username,
            display_name=payload.display_name,
            print_limit=payload.print_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return UserProfileOut.model_validate(profile)

