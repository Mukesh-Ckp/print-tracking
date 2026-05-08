"""Schemas for the print_logs API surface."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.print_log import PrintStatus


class PrintLogCreate(BaseModel):
    """Payload submitted by the print-agent for each detected print job."""

    username: Optional[str] = Field(default=None, max_length=128)
    computer_name: Optional[str] = Field(default=None, max_length=128)
    laptop_ip: Optional[str] = Field(default=None, max_length=64)

    printer_name: Optional[str] = Field(default=None, max_length=255)
    printer_ip: Optional[str] = Field(default=None, max_length=64)

    document_name: Optional[str] = Field(default=None, max_length=512)
    pages: int = Field(default=0, ge=0, le=100000)
    copies: int = Field(default=1, ge=0, le=10000)
    total_pages: int = Field(default=0, ge=0, le=1000000)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    paper_size: Optional[str] = Field(default=None, max_length=64)
    color_mode: Optional[str] = Field(default=None, max_length=32)
    duplex: Optional[str] = Field(default=None, max_length=32)

    status: PrintStatus = PrintStatus.UNKNOWN
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(default=None, ge=0)

    job_id: Optional[str] = Field(default=None, max_length=128)
    raw_payload: Optional[str] = None


class PrintLogOut(BaseModel):
    id: int
    username: Optional[str] = None
    display_username: Optional[str] = None
    computer_name: Optional[str] = None
    laptop_ip: Optional[str] = None
    printer_name: Optional[str] = None
    printer_ip: Optional[str] = None
    document_name: Optional[str] = None
    pages: int = 0
    copies: int = 1
    total_pages: int = 0
    size_bytes: Optional[int] = None
    paper_size: Optional[str] = None
    color_mode: Optional[str] = None
    duplex: Optional[str] = None
    status: PrintStatus
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    user_limit_exceeded: bool = False
    job_id: Optional[str] = None
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrintLogQuery(BaseModel):
    """Query/filter parameters used by GET /api/prints."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)
    search: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = None
    computer_name: Optional[str] = None
    printer_name: Optional[str] = None
    status: Optional[PrintStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PaginatedPrintLogs(BaseModel):
    items: List[PrintLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int
