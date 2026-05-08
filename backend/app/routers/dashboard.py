"""Dashboard summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..database.session import get_db
from ..models.admin import Admin
from ..schemas.dashboard import DashboardResponse
from ..services.stats_service import build_dashboard

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Single payload powering the admin dashboard landing page.",
)
def dashboard(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
) -> DashboardResponse:
    return build_dashboard(db)
