"""Business logic for storing and querying print logs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..models.print_log import PrintLog, PrintStatus
from ..models.printer import Printer
from ..models.user_profile import UserProfile
from ..schemas.print_log import PrintLogCreate, PrintLogQuery

logger = logging.getLogger(__name__)


def _coerce_total_pages(payload: PrintLogCreate) -> int:
    """Compute total pages = pages * copies (with sensible fallbacks)."""
    if payload.total_pages and payload.total_pages > 0:
        return payload.total_pages
    pages = payload.pages or 0
    copies = payload.copies or 1
    return max(pages * max(copies, 1), 0)


def upsert_printer_seen(
    db: Session,
    *,
    name: str | None,
    ip: str | None,
    network: str | None = None,
    model: str | None = None,
    commit: bool = True,
) -> Printer | None:
    """Insert/update the printers registry whenever the agent reports a new device."""
    if not name:
        return None

    printer = db.query(Printer).filter(Printer.name == name).first()
    now = datetime.now(timezone.utc)
    if printer is None:
        printer = Printer(
            name=name,
            ip_address=ip,
            model=model,
            network=network,
            is_active=True,
            last_seen_at=now,
        )
        db.add(printer)
    else:
        printer.last_seen_at = now
        printer.is_active = True
        if ip and not printer.ip_address:
            printer.ip_address = ip
        if model and not printer.model:
            printer.model = model
        if network and not printer.network:
            printer.network = network
    if commit:
        db.commit()
        db.refresh(printer)
    return printer


def create_print_log(db: Session, payload: PrintLogCreate) -> PrintLog:
    """Persist a print job submitted by the on-premise agent."""
    total_pages = _coerce_total_pages(payload)
    raw_username = payload.username or "unknown"
    profile = db.query(UserProfile).filter(UserProfile.raw_username == raw_username).first()
    display_username = profile.display_name.strip() if (profile and profile.display_name) else raw_username

    # If the user has a print-job limit, flag jobs AFTER crossing that limit.
    prior_jobs_count = int(
        db.query(func.count(PrintLog.id))
        .filter(PrintLog.username == raw_username)
        .scalar()
        or 0
    )
    limit_exceeded = bool(
        profile
        and profile.print_limit is not None
        and profile.print_limit > 0
        and prior_jobs_count >= profile.print_limit
    )

    log = PrintLog(
        username=raw_username,
        display_username=display_username,
        computer_name=payload.computer_name,
        laptop_ip=payload.laptop_ip,
        printer_name=payload.printer_name,
        printer_ip=payload.printer_ip,
        document_name=payload.document_name,
        pages=payload.pages or 0,
        copies=payload.copies or 1,
        total_pages=total_pages,
        size_bytes=payload.size_bytes,
        paper_size=payload.paper_size,
        color_mode=payload.color_mode,
        duplex=payload.duplex,
        status=payload.status or PrintStatus.UNKNOWN,
        submitted_at=payload.submitted_at,
        completed_at=payload.completed_at,
        duration_seconds=payload.duration_seconds,
        user_limit_exceeded=limit_exceeded,
        job_id=payload.job_id,
        raw_payload=payload.raw_payload,
    )
    db.add(log)

    # Update printer registry without forcing an extra commit.
    upsert_printer_seen(
        db,
        name=payload.printer_name,
        ip=payload.printer_ip,
        commit=False,
    )

    db.commit()
    db.refresh(log)
    return log


def upsert_user_profile(
    db: Session,
    *,
    raw_username: str,
    display_name: str | None,
    print_limit: int | None,
) -> UserProfile:
    """
    Create or update a user profile mapping and limit.

    Also re-applies display names and limit-exceeded flags to existing
    print logs so the UI stays consistent across old and new rows.
    """
    raw_username = (raw_username or "").strip()
    if not raw_username:
        raise ValueError("raw_username is required")

    profile = db.query(UserProfile).filter(UserProfile.raw_username == raw_username).first()
    if profile is None:
        profile = UserProfile(raw_username=raw_username)
        db.add(profile)

    profile.display_name = display_name.strip() if display_name else None
    profile.print_limit = int(print_limit) if print_limit else None

    _reapply_profile_on_existing_logs(db, raw_username=raw_username, profile=profile)
    db.commit()
    db.refresh(profile)
    return profile


def _reapply_profile_on_existing_logs(
    db: Session, *, raw_username: str, profile: UserProfile
) -> None:
    """Recompute display name and over-limit flags for existing user logs."""
    rows = (
        db.query(PrintLog)
        .filter(PrintLog.username == raw_username)
        .order_by(PrintLog.received_at.asc(), PrintLog.id.asc())
        .all()
    )
    display = profile.display_name.strip() if profile.display_name else raw_username
    limit = profile.print_limit if (profile.print_limit and profile.print_limit > 0) else None
    for idx, row in enumerate(rows, start=1):
        row.display_username = display
        row.user_limit_exceeded = bool(limit and idx > limit)


def list_user_summaries(db: Session) -> list[dict]:
    """List known users with print counts, limits and exceeded totals."""
    users = (
        db.query(PrintLog.username)
        .filter(PrintLog.username.isnot(None))
        .distinct()
        .all()
    )
    out: list[dict] = []
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for (username,) in users:
        if not username:
            continue
        profile = db.query(UserProfile).filter(UserProfile.raw_username == username).first()
        total = int(
            db.query(func.count(PrintLog.id))
            .filter(PrintLog.username == username)
            .scalar()
            or 0
        )
        today = int(
            db.query(func.count(PrintLog.id))
            .filter(PrintLog.username == username)
            .filter(PrintLog.received_at >= today_start)
            .scalar()
            or 0
        )
        exceeded = int(
            db.query(func.count(PrintLog.id))
            .filter(PrintLog.username == username)
            .filter(PrintLog.user_limit_exceeded.is_(True))
            .scalar()
            or 0
        )
        display_name = profile.display_name if profile else None
        out.append(
            {
                "username": username,
                "display_name": display_name,
                "effective_name": display_name or username,
                "print_limit": profile.print_limit if profile else None,
                "prints_total": total,
                "prints_today": today,
                "over_limit_count": exceeded,
            }
        )
    out.sort(key=lambda row: row["prints_total"], reverse=True)
    return out


def _apply_filters(q, *, search, username, computer_name, printer_name, status, date_from, date_to):
    """Build the WHERE clause shared by paginated listing and exports."""
    filters = []
    if username:
        filters.append(PrintLog.username == username)
    if computer_name:
        filters.append(PrintLog.computer_name == computer_name)
    if printer_name:
        filters.append(PrintLog.printer_name == printer_name)
    if status:
        filters.append(PrintLog.status == status)
    if date_from:
        filters.append(PrintLog.received_at >= date_from)
    if date_to:
        filters.append(PrintLog.received_at <= date_to)
    if search:
        like = f"%{search.strip()}%"
        filters.append(
            or_(
                PrintLog.document_name.ilike(like),
                PrintLog.username.ilike(like),
                PrintLog.computer_name.ilike(like),
                PrintLog.printer_name.ilike(like),
                PrintLog.laptop_ip.ilike(like),
                PrintLog.job_id.ilike(like),
            )
        )
    if filters:
        q = q.filter(and_(*filters))
    return q


def list_print_logs(
    db: Session, query: PrintLogQuery
) -> Tuple[list[PrintLog], int]:
    """Return (page_items, total_count) for the given filter parameters."""
    q = _apply_filters(
        db.query(PrintLog),
        search=query.search,
        username=query.username,
        computer_name=query.computer_name,
        printer_name=query.printer_name,
        status=query.status,
        date_from=query.date_from,
        date_to=query.date_to,
    )

    total = q.count()
    items = (
        q.order_by(PrintLog.received_at.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
        .all()
    )
    return items, total


def export_print_logs(
    db: Session,
    *,
    search=None,
    username=None,
    computer_name=None,
    printer_name=None,
    status=None,
    date_from=None,
    date_to=None,
    limit: int = 5000,
) -> list[PrintLog]:
    """Return up to ``limit`` rows matching the supplied filters (no pagination)."""
    q = _apply_filters(
        db.query(PrintLog),
        search=search,
        username=username,
        computer_name=computer_name,
        printer_name=printer_name,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return (
        q.order_by(PrintLog.received_at.desc())
        .limit(max(1, limit))
        .all()
    )
