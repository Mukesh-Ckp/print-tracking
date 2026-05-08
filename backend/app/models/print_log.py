"""Print log model: one row per print job tracked by the on-premise agent."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database.session import Base


class PrintStatus(str, enum.Enum):
    """Lifecycle status of a print job as observed in the Windows spooler."""

    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class PrintLog(Base):
    """A single print job captured by the print-agent and persisted to the DB."""

    __tablename__ = "print_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity / origin
    username: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    display_username: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    computer_name: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    laptop_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # Printer
    printer_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    printer_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # Job details
    document_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paper_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duplex: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Status / time
    status: Mapped[PrintStatus] = mapped_column(
        SAEnum(PrintStatus, name="print_status", native_enum=False, length=32),
        default=PrintStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Alert if this job exceeds the configured per-user print-job limit.
    user_limit_exceeded: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    # Bookkeeping
    job_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_print_logs_received_status", "received_at", "status"),
        Index("ix_print_logs_user_received", "username", "received_at"),
        Index("ix_print_logs_printer_received", "printer_name", "received_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PrintLog id={self.id} user={self.username} "
            f"doc={self.document_name!r} pages={self.total_pages} status={self.status}>"
        )
