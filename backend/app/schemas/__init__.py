"""Pydantic schemas for request validation and response serialisation."""

from .auth import LoginRequest, TokenResponse
from .admin import AdminOut
from .common import HealthResponse, MessageResponse
from .dashboard import (
    DashboardResponse,
    PrinterStat,
    StatsResponse,
    TimeSeriesPoint,
    TopUserStat,
)
from .print_log import (
    PaginatedPrintLogs,
    PrintLogCreate,
    PrintLogOut,
    PrintLogQuery,
)
from .printer import PrinterOut
from .user_profile import UserProfileOut, UserProfileUpdate, UserSummaryOut

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "AdminOut",
    "HealthResponse",
    "MessageResponse",
    "DashboardResponse",
    "PrinterStat",
    "StatsResponse",
    "TimeSeriesPoint",
    "TopUserStat",
    "PaginatedPrintLogs",
    "PrintLogCreate",
    "PrintLogOut",
    "PrintLogQuery",
    "PrinterOut",
    "UserProfileOut",
    "UserProfileUpdate",
    "UserSummaryOut",
]
