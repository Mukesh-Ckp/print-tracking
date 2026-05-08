"""Printer schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PrinterOut(BaseModel):
    id: int
    name: str
    ip_address: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    network: Optional[str] = None
    is_active: bool = True
    last_seen_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
