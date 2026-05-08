"""Schemas for user profile mapping and print limits."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)
    print_limit: Optional[int] = Field(default=None, ge=1, le=100000)


class UserProfileOut(BaseModel):
    id: int
    raw_username: str
    display_name: Optional[str] = None
    print_limit: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSummaryOut(BaseModel):
    username: str
    display_name: Optional[str] = None
    effective_name: str
    print_limit: Optional[int] = None
    prints_total: int = 0
    prints_today: int = 0
    over_limit_count: int = 0

