"""Report endpoints: PDF / Excel exports of filtered print logs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin
from ..database.session import get_db
from ..models.admin import Admin
from ..models.print_log import PrintStatus
from ..services.activity_service import log_activity
from ..services.print_service import export_print_logs
from ..services.report_service import build_excel_report, build_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])

MAX_EXPORT_ROWS = 5000


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime: {value!r}",
        )


def _gather_logs(
    db: Session,
    *,
    search: Optional[str],
    username: Optional[str],
    computer_name: Optional[str],
    printer_name: Optional[str],
    job_status: Optional[PrintStatus],
    date_from: Optional[str],
    date_to: Optional[str],
):
    return export_print_logs(
        db,
        search=search,
        username=username,
        computer_name=computer_name,
        printer_name=printer_name,
        status=job_status,
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to),
        limit=MAX_EXPORT_ROWS,
    )


@router.get(
    "",
    summary="List of available report formats.",
)
def list_reports(
    _: Admin = Depends(get_current_admin),
):
    return {
        "available_formats": ["pdf", "excel"],
        "max_rows_per_export": MAX_EXPORT_ROWS,
        "endpoints": {
            "pdf": "/api/reports/pdf",
            "excel": "/api/reports/excel",
        },
    }


@router.get("/excel", summary="Download print logs as an .xlsx file.")
def export_excel(
    request: Request,
    search: Optional[str] = None,
    username: Optional[str] = None,
    computer_name: Optional[str] = None,
    printer_name: Optional[str] = None,
    job_status: Optional[PrintStatus] = Query(None, alias="status"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    logs = _gather_logs(
        db,
        search=search,
        username=username,
        computer_name=computer_name,
        printer_name=printer_name,
        job_status=job_status,
        date_from=date_from,
        date_to=date_to,
    )
    data = build_excel_report(logs)
    log_activity(
        db,
        actor=current.username,
        action="export_excel",
        target=f"{len(logs)} rows",
        ip_address=request.client.host if request.client else None,
    )
    filename = f"print_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf", summary="Download print logs as a PDF report.")
def export_pdf(
    request: Request,
    search: Optional[str] = None,
    username: Optional[str] = None,
    computer_name: Optional[str] = None,
    printer_name: Optional[str] = None,
    job_status: Optional[PrintStatus] = Query(None, alias="status"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    logs = _gather_logs(
        db,
        search=search,
        username=username,
        computer_name=computer_name,
        printer_name=printer_name,
        job_status=job_status,
        date_from=date_from,
        date_to=date_to,
    )

    subtitle_bits = []
    if date_from:
        subtitle_bits.append(f"from {date_from}")
    if date_to:
        subtitle_bits.append(f"to {date_to}")
    if username:
        subtitle_bits.append(f"user={username}")
    if printer_name:
        subtitle_bits.append(f"printer={printer_name}")
    subtitle = ", ".join(subtitle_bits) if subtitle_bits else "All print activity"

    data = build_pdf_report(logs, title="Print Logs Report", subtitle=subtitle)
    log_activity(
        db,
        actor=current.username,
        action="export_pdf",
        target=f"{len(logs)} rows",
        ip_address=request.client.host if request.client else None,
    )
    filename = f"print_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
