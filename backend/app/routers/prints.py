"""
Print-job routes.

* POST /api/print-log  -> ingestion endpoint used by the on-premise print-agent.
                          Authenticated via the static X-API-Key header.
* GET  /api/prints     -> paginated, filterable listing for the dashboard.
                          Authenticated via admin JWT.
* GET  /api/prints/{id}  -> single print log details.
* DELETE /api/prints/{id} -> remove a print log (super-admin).
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_admin, require_agent_api_key
from ..database.session import get_db
from ..models.admin import Admin
from ..models.print_log import PrintLog, PrintStatus
from ..schemas.print_log import (
    PaginatedPrintLogs,
    PrintLogCreate,
    PrintLogOut,
    PrintLogQuery,
)
from ..services.print_service import create_print_log, list_print_logs

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prints"])


# ---------------------------------------------------------------------------
# Ingestion (called by the print-agent service)
# ---------------------------------------------------------------------------
@router.post(
    "/print-log",
    response_model=PrintLogOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_agent_api_key)],
    summary="Ingest a print job from the on-premise print-agent.",
)
def ingest_print_log(payload: PrintLogCreate, db: Session = Depends(get_db)) -> PrintLogOut:
    log = create_print_log(db, payload)
    logger.info(
        "Print log ingested id=%s user=%s doc=%s pages=%s status=%s",
        log.id,
        log.username,
        log.document_name,
        log.total_pages,
        log.status,
    )
    return PrintLogOut.model_validate(log)


# ---------------------------------------------------------------------------
# Dashboard read APIs (require admin JWT)
# ---------------------------------------------------------------------------
@router.get(
    "/prints",
    response_model=PaginatedPrintLogs,
    summary="Paginated list of print jobs with filtering.",
)
def list_prints(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=255),
    username: Optional[str] = None,
    computer_name: Optional[str] = None,
    printer_name: Optional[str] = None,
    job_status: Optional[PrintStatus] = Query(None, alias="status"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
) -> PaginatedPrintLogs:
    from datetime import datetime

    def parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime: {value!r}",
            )

    q = PrintLogQuery(
        page=page,
        page_size=page_size,
        search=search,
        username=username,
        computer_name=computer_name,
        printer_name=printer_name,
        status=job_status,
        date_from=parse_dt(date_from),
        date_to=parse_dt(date_to),
    )
    items, total = list_print_logs(db, q)
    total_pages = max(1, math.ceil(total / page_size)) if total else 1

    return PaginatedPrintLogs(
        items=[PrintLogOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/prints/{print_id}",
    response_model=PrintLogOut,
    summary="Fetch a single print log entry.",
)
def get_print(
    print_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
) -> PrintLogOut:
    log = db.query(PrintLog).filter(PrintLog.id == print_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Print log not found.")
    return PrintLogOut.model_validate(log)


@router.delete(
    "/prints/{print_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a print log entry (super-admin only).",
)
def delete_print(
    print_id: int,
    db: Session = Depends(get_db),
    current: Admin = Depends(get_current_admin),
):
    if not current.is_superuser:
        raise HTTPException(status_code=403, detail="Super-admin privileges required.")
    log = db.query(PrintLog).filter(PrintLog.id == print_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Print log not found.")
    db.delete(log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
