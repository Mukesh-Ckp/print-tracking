"""KPI / stats endpoint (lightweight version of /dashboard)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..database.session import get_db
from ..models.admin import Admin
from ..models.printer import Printer
from ..schemas.dashboard import StatsResponse
from ..schemas.printer import PrinterOut
from ..services.stats_service import build_stats

router = APIRouter(tags=["stats"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="KPI numbers for dashboard cards.",
)
def get_stats(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
) -> StatsResponse:
    return build_stats(db)


@router.get(
    "/printers",
    response_model=list[PrinterOut],
    summary="Registered printers.",
)
def list_printers(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
) -> list[PrinterOut]:
    rows = db.query(Printer).order_by(Printer.last_seen_at.desc().nullslast()).all()
    return [PrinterOut.model_validate(p) for p in rows]
