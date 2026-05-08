"""
Aggregation helpers used by /api/stats and /api/dashboard.

All time-series queries are expressed in raw SQL fragments through
``func.date_trunc`` (Postgres) with a SQLite fallback to keep local
development friction-free.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.session import engine
from ..models.print_log import PrintLog, PrintStatus
from ..models.printer import Printer
from ..schemas.dashboard import (
    DashboardResponse,
    PrinterStat,
    StatsResponse,
    TimeSeriesPoint,
    TopUserStat,
)
from ..schemas.print_log import PrintLogOut


def _start_of_day(dt: datetime) -> datetime:
    return datetime.combine(dt.date(), time.min, tzinfo=timezone.utc)


def _is_postgres() -> bool:
    return engine.dialect.name in ("postgresql", "postgres")


def build_stats(db: Session) -> StatsResponse:
    """Compute KPI numbers for the dashboard top cards."""
    now = datetime.now(timezone.utc)
    today_start = _start_of_day(now)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    def count_and_pages(filter_clause):
        q = db.query(
            func.count(PrintLog.id),
            func.coalesce(func.sum(PrintLog.total_pages), 0),
        ).filter(filter_clause)
        prints, pages = q.one()
        return int(prints or 0), int(pages or 0)

    prints_today, pages_today = count_and_pages(PrintLog.received_at >= today_start)
    prints_week, pages_week = count_and_pages(PrintLog.received_at >= week_start)
    prints_month, pages_month = count_and_pages(PrintLog.received_at >= month_start)

    total_prints = int(db.query(func.count(PrintLog.id)).scalar() or 0)
    total_pages = int(
        db.query(func.coalesce(func.sum(PrintLog.total_pages), 0)).scalar() or 0
    )

    active_users_today = int(
        db.query(func.count(func.distinct(PrintLog.username)))
        .filter(PrintLog.received_at >= today_start)
        .filter(PrintLog.username.isnot(None))
        .scalar()
        or 0
    )
    active_printers = int(
        db.query(func.count(Printer.id)).filter(Printer.is_active.is_(True)).scalar() or 0
    )
    failed_today = int(
        db.query(func.count(PrintLog.id))
        .filter(PrintLog.received_at >= today_start)
        .filter(PrintLog.status == PrintStatus.FAILED)
        .scalar()
        or 0
    )

    return StatsResponse(
        prints_today=prints_today,
        pages_today=pages_today,
        prints_this_week=prints_week,
        pages_this_week=pages_week,
        prints_this_month=prints_month,
        pages_this_month=pages_month,
        prints_total=total_prints,
        pages_total=total_pages,
        active_users_today=active_users_today,
        active_printers=active_printers,
        failed_today=failed_today,
    )


def _hourly_today(db: Session, now: datetime) -> List[TimeSeriesPoint]:
    """24-bucket time series of prints/pages over today (00:00 -> current hour)."""
    today_start = _start_of_day(now)

    rows = (
        db.query(
            PrintLog.received_at,
            PrintLog.total_pages,
        )
        .filter(PrintLog.received_at >= today_start)
        .all()
    )

    buckets: dict[int, dict[str, int]] = {h: {"prints": 0, "pages": 0} for h in range(24)}
    for received_at, total_pages in rows:
        if received_at is None:
            continue
        hour = received_at.hour
        buckets[hour]["prints"] += 1
        buckets[hour]["pages"] += int(total_pages or 0)

    return [
        TimeSeriesPoint(
            label=f"{h:02d}:00",
            timestamp=today_start.replace(hour=h),
            prints=buckets[h]["prints"],
            pages=buckets[h]["pages"],
        )
        for h in range(24)
    ]


def _daily_last_30(db: Session, now: datetime) -> List[TimeSeriesPoint]:
    """30-day daily time series of print volume."""
    today_start = _start_of_day(now)
    start = today_start - timedelta(days=29)

    rows = (
        db.query(PrintLog.received_at, PrintLog.total_pages)
        .filter(PrintLog.received_at >= start)
        .all()
    )

    buckets: dict[str, dict[str, int]] = {}
    for i in range(30):
        d = (start + timedelta(days=i)).date().isoformat()
        buckets[d] = {"prints": 0, "pages": 0}

    for received_at, total_pages in rows:
        if received_at is None:
            continue
        key = received_at.date().isoformat()
        if key in buckets:
            buckets[key]["prints"] += 1
            buckets[key]["pages"] += int(total_pages or 0)

    out: List[TimeSeriesPoint] = []
    for i in range(30):
        d = start + timedelta(days=i)
        key = d.date().isoformat()
        out.append(
            TimeSeriesPoint(
                label=key,
                timestamp=d,
                prints=buckets[key]["prints"],
                pages=buckets[key]["pages"],
            )
        )
    return out


def _top_users(db: Session, now: datetime, limit: int = 5) -> List[TopUserStat]:
    month_start = _start_of_day(now).replace(day=1)
    rows = (
        db.query(
            PrintLog.username,
            func.count(PrintLog.id),
            func.coalesce(func.sum(PrintLog.total_pages), 0),
        )
        .filter(PrintLog.received_at >= month_start)
        .filter(PrintLog.username.isnot(None))
        .group_by(PrintLog.username)
        .order_by(func.count(PrintLog.id).desc())
        .limit(limit)
        .all()
    )
    return [
        TopUserStat(username=u or "unknown", prints=int(p or 0), pages=int(g or 0))
        for u, p, g in rows
    ]


def _top_printers(db: Session, now: datetime, limit: int = 5) -> List[PrinterStat]:
    month_start = _start_of_day(now).replace(day=1)
    rows = (
        db.query(
            PrintLog.printer_name,
            func.count(PrintLog.id),
            func.coalesce(func.sum(PrintLog.total_pages), 0),
        )
        .filter(PrintLog.received_at >= month_start)
        .filter(PrintLog.printer_name.isnot(None))
        .group_by(PrintLog.printer_name)
        .order_by(func.count(PrintLog.id).desc())
        .limit(limit)
        .all()
    )
    return [
        PrinterStat(printer_name=n or "unknown", prints=int(p or 0), pages=int(g or 0))
        for n, p, g in rows
    ]


def _status_breakdown(db: Session, now: datetime) -> dict:
    month_start = _start_of_day(now).replace(day=1)
    rows = (
        db.query(PrintLog.status, func.count(PrintLog.id))
        .filter(PrintLog.received_at >= month_start)
        .group_by(PrintLog.status)
        .all()
    )
    out: dict[str, int] = {s.value: 0 for s in PrintStatus}
    for status, count in rows:
        key = status.value if hasattr(status, "value") else str(status)
        out[key] = int(count or 0)
    return out


def build_dashboard(db: Session) -> DashboardResponse:
    """Build the comprehensive payload powering the dashboard landing page."""
    now = datetime.now(timezone.utc)

    stats = build_stats(db)
    recent = (
        db.query(PrintLog)
        .order_by(PrintLog.received_at.desc())
        .limit(15)
        .all()
    )
    over_limit_alerts = (
        db.query(PrintLog)
        .filter(PrintLog.user_limit_exceeded.is_(True))
        .order_by(PrintLog.received_at.desc())
        .limit(20)
        .all()
    )
    over_limit_alert_count = int(
        db.query(func.count(PrintLog.id))
        .filter(PrintLog.user_limit_exceeded.is_(True))
        .scalar()
        or 0
    )

    return DashboardResponse(
        stats=stats,
        recent_prints=[PrintLogOut.model_validate(r) for r in recent],
        hourly_today=_hourly_today(db, now),
        daily_last_30_days=_daily_last_30(db, now),
        top_users=_top_users(db, now),
        top_printers=_top_printers(db, now),
        status_breakdown=_status_breakdown(db, now),
        over_limit_alert_count=over_limit_alert_count,
        over_limit_alerts=[PrintLogOut.model_validate(r) for r in over_limit_alerts],
        generated_at=now,
    )
