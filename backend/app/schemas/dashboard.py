"""Dashboard / analytics schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .print_log import PrintLogOut


class TimeSeriesPoint(BaseModel):
    label: str  # e.g. "2026-05-07" or "12:00"
    timestamp: Optional[datetime] = None
    prints: int = 0
    pages: int = 0


class TopUserStat(BaseModel):
    username: str
    prints: int
    pages: int


class PrinterStat(BaseModel):
    printer_name: str
    prints: int
    pages: int


class StatsResponse(BaseModel):
    """Summary numbers shown as KPI cards on the dashboard."""

    prints_today: int = 0
    pages_today: int = 0
    prints_this_week: int = 0
    pages_this_week: int = 0
    prints_this_month: int = 0
    pages_this_month: int = 0
    prints_total: int = 0
    pages_total: int = 0
    active_users_today: int = 0
    active_printers: int = 0
    failed_today: int = 0


class DashboardResponse(BaseModel):
    """Single payload that powers the React dashboard landing page."""

    stats: StatsResponse
    recent_prints: List[PrintLogOut]
    hourly_today: List[TimeSeriesPoint]
    daily_last_30_days: List[TimeSeriesPoint]
    top_users: List[TopUserStat]
    top_printers: List[PrinterStat]
    status_breakdown: dict
    over_limit_alert_count: int = 0
    over_limit_alerts: List[PrintLogOut]
    generated_at: datetime
