"""
Windows print-spooler monitor.

Strategy
--------

Every ``poll_interval_seconds`` we enumerate all print queues with
``win32print`` and snapshot every active job. Jobs are tracked by
``(printer_name, job_id)``. When a job we previously saw disappears
from the queue we treat that as completion (or cancellation/failure if
the last observed status indicates so).

Why polling instead of ``FindFirstPrinterChangeNotification``?

* The notification API requires admin/SYSTEM rights or running inside
  the spooler service context which is fragile to ship to customer PCs.
* Polling the queue with ``EnumJobs`` is well-supported, very cheap
  (a few µs per query) and works equally well for local & shared queues.
* Every observed transition is captured, so even brief print jobs are
  recorded.

This file intentionally guards every Windows-specific import so the
module can be syntax-checked on non-Windows CI machines.
"""

from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from .config import AgentConfig
from .system_info import get_host_info

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional Windows imports
# ---------------------------------------------------------------------------
_IS_WINDOWS = platform.system().lower().startswith("win")

if _IS_WINDOWS:
    try:
        import win32print  # type: ignore
    except ImportError:  # pragma: no cover - depends on environment
        win32print = None  # type: ignore
        logger.warning("pywin32 not available; spooler monitor will be inert.")
else:
    win32print = None  # type: ignore


# ---------------------------------------------------------------------------
# JOB_INFO_2 status flags (subset)
# ---------------------------------------------------------------------------
JOB_STATUS_FLAGS: List[Tuple[int, str]] = [
    (0x00000001, "paused"),
    (0x00000002, "error"),
    (0x00000004, "deleting"),
    (0x00000010, "printing"),
    (0x00000020, "offline"),
    (0x00000040, "paper_out"),
    (0x00000080, "printed"),
    (0x00000100, "deleted"),
    (0x00000200, "blocked_devq"),
    (0x00000400, "user_intervention"),
    (0x00000800, "restart"),
    (0x00001000, "complete"),
    (0x00002000, "retained"),
    (0x00004000, "rendering_locally"),
]

# Mapping to canonical statuses understood by the backend.
STATUS_PRIORITIES = [
    ("failed", ["error", "deleted", "blocked_devq", "paper_out", "offline", "user_intervention"]),
    ("completed", ["printed", "complete"]),
    ("cancelled", ["deleting"]),
    ("paused", ["paused"]),
    ("printing", ["printing", "rendering_locally", "restart"]),
]


def _decode_status(status_flags: int) -> Tuple[str, List[str]]:
    """Translate Windows status bitmask to (canonical, raw_flags)."""
    raw = [name for bit, name in JOB_STATUS_FLAGS if status_flags & bit]
    for canonical, names in STATUS_PRIORITIES:
        if any(n in raw for n in names):
            return canonical, raw
    if status_flags == 0:
        return "queued", raw
    return "unknown", raw


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class JobSnapshot:
    """A single sample of a print job at a given polling tick."""

    printer_name: str
    job_id: int
    document_name: str
    username: str
    pages: int
    copies: int
    size_bytes: int
    status_flags: int
    submitted_at: Optional[datetime]
    paper_size: Optional[str] = None


@dataclass
class TrackedJob:
    """In-memory view of a print job, updated across polling ticks."""

    printer_name: str
    job_id: int
    document_name: str
    username: str
    pages: int
    copies: int
    size_bytes: int
    submitted_at: Optional[datetime]
    last_seen_at: datetime
    last_status: str = "queued"
    raw_flags: List[str] = field(default_factory=list)
    paper_size: Optional[str] = None

    def to_payload(
        self, *, status: str, completed_at: Optional[datetime], extra: Dict
    ) -> Dict:
        host = get_host_info()
        total_pages = max(self.pages * max(self.copies, 1), self.pages)
        duration = None
        if self.submitted_at and completed_at:
            duration = max(0.0, (completed_at - self.submitted_at).total_seconds())

        payload: Dict = {
            "username": self.username or host.username,
            "computer_name": host.computer_name,
            "laptop_ip": host.primary_ip,
            "printer_name": self.printer_name,
            "printer_ip": extra.get("printer_ip"),
            "document_name": self.document_name,
            "pages": int(self.pages or 0),
            "copies": int(self.copies or 1),
            "total_pages": int(total_pages or 0),
            "size_bytes": int(self.size_bytes or 0) or None,
            "paper_size": self.paper_size,
            "color_mode": extra.get("color_mode"),
            "duplex": extra.get("duplex"),
            "status": status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "duration_seconds": duration,
            "job_id": f"{self.printer_name}:{self.job_id}",
            "raw_payload": ",".join(self.raw_flags) if self.raw_flags else None,
        }
        return payload


# ---------------------------------------------------------------------------
# Spooler enumeration helpers
# ---------------------------------------------------------------------------
def _safe_to_dt(value) -> Optional[datetime]:
    """Convert pywin32 SYSTEMTIME-like values to UTC ``datetime``."""
    if value is None:
        return None
    try:
        # pywin32 returns datetime instances directly for SYSTEMTIME fields.
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        # Some pywin32 versions wrap in PyTime objects which support .Format().
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except Exception:  # pragma: no cover - defensive
        return None


def _enumerate_printers() -> List[Tuple[str, Optional[str]]]:
    """Return [(printer_name, port_or_ip), ...] for every printer the host can see."""
    if win32print is None:
        return []
    printers: List[Tuple[str, Optional[str]]] = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    try:
        for entry in win32print.EnumPrinters(flags, None, 2):
            name = entry.get("pPrinterName")
            port = entry.get("pPortName")
            if name:
                printers.append((name, port))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("EnumPrinters failed: %s", exc)
    return printers


def _enumerate_jobs(printer_name: str) -> List[JobSnapshot]:
    """List all queued/active jobs for one printer."""
    if win32print is None:
        return []
    snapshots: List[JobSnapshot] = []
    try:
        handle = win32print.OpenPrinter(printer_name)
    except Exception as exc:
        logger.debug("OpenPrinter(%s) failed: %s", printer_name, exc)
        return snapshots
    try:
        try:
            info = win32print.GetPrinter(handle, 2)
            total_jobs = int(info.get("cJobs", 0)) if isinstance(info, dict) else 0
        except Exception:
            total_jobs = 0

        # Always ask for a generous window even when EnumJobs returns 0 -- some
        # pywin32 versions only show jobs once they actually start spooling.
        max_jobs = max(total_jobs * 2, 64)
        try:
            jobs = win32print.EnumJobs(handle, 0, max_jobs, 2) or []
        except Exception as exc:
            logger.debug("EnumJobs(%s) failed: %s", printer_name, exc)
            jobs = []

        for job in jobs:
            try:
                snapshots.append(
                    JobSnapshot(
                        printer_name=printer_name,
                        job_id=int(job.get("JobId", 0)),
                        document_name=str(job.get("pDocument") or "(untitled)"),
                        username=str(job.get("pUserName") or ""),
                        pages=int(job.get("TotalPages") or job.get("PagesPrinted") or 0),
                        copies=1,  # Windows JOB_INFO_2 doesn't expose copies separately.
                        size_bytes=int(job.get("Size") or 0),
                        status_flags=int(job.get("Status", 0)),
                        submitted_at=_safe_to_dt(job.get("Submitted")),
                        paper_size=None,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Failed to parse job for %s: %s", printer_name, exc)
    finally:
        try:
            win32print.ClosePrinter(handle)
        except Exception:  # pragma: no cover - defensive
            pass
    return snapshots


def _port_to_ip(port: Optional[str]) -> Optional[str]:
    """Best-effort conversion of a Windows printer port string to an IP address."""
    if not port:
        return None
    p = port.strip()
    # Common forms: "IP_192.168.1.131", "192.168.1.131", "WSD-...", "USB001".
    if p.startswith("IP_"):
        return p[3:]
    parts = p.split(".")
    if len(parts) == 4 and all(seg.isdigit() and 0 <= int(seg) <= 255 for seg in parts):
        return p
    return None


# ---------------------------------------------------------------------------
# Spooler monitor (public)
# ---------------------------------------------------------------------------
class SpoolerMonitor:
    """Polls the Windows spooler and emits print events to a callback."""

    def __init__(
        self,
        cfg: AgentConfig,
        on_event: Callable[[Dict], None],
    ) -> None:
        self.cfg = cfg
        self.on_event = on_event
        self._tracked: Dict[Tuple[str, int], TrackedJob] = {}
        self._missing_since: Dict[Tuple[str, int], datetime] = {}
        self._printer_ports: Dict[str, Optional[str]] = {}
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    # ------------------------------------------------------------------
    # Public main loop
    # ------------------------------------------------------------------
    def run_forever(self) -> None:
        if not _IS_WINDOWS:
            logger.error("Print spooler monitoring requires Windows.")
            return
        if win32print is None:
            logger.error("pywin32 is not installed; cannot monitor spooler.")
            return

        logger.info(
            "Spooler monitor starting; poll_interval=%.2fs whitelist=%s",
            self.cfg.poll_interval_seconds,
            self.cfg.printer_whitelist or "<all printers>",
        )

        while not self._stop:
            try:
                self._tick()
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Spooler poll failed: %s", exc)
            time.sleep(self.cfg.poll_interval_seconds)

    # ------------------------------------------------------------------
    # Per-tick logic
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        now = datetime.now(timezone.utc)

        # 1) Refresh known printer ports.
        printers = _enumerate_printers()
        whitelist = {p.lower() for p in self.cfg.printer_whitelist}
        for name, port in printers:
            self._printer_ports[name] = port

        # 2) Snapshot every job currently in every queue.
        seen_keys: set[Tuple[str, int]] = set()
        for printer_name, _port in printers:
            if whitelist and printer_name.lower() not in whitelist:
                continue
            try:
                snapshots = _enumerate_jobs(printer_name)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Could not enumerate jobs for %s: %s", printer_name, exc)
                continue

            for snap in snapshots:
                key = (snap.printer_name, snap.job_id)
                seen_keys.add(key)
                self._missing_since.pop(key, None)
                tracked = self._tracked.get(key)
                canonical, raw_flags = _decode_status(snap.status_flags)
                if tracked is None:
                    tracked = TrackedJob(
                        printer_name=snap.printer_name,
                        job_id=snap.job_id,
                        document_name=snap.document_name,
                        username=snap.username,
                        pages=snap.pages,
                        copies=snap.copies,
                        size_bytes=snap.size_bytes,
                        submitted_at=snap.submitted_at,
                        last_seen_at=now,
                        last_status=canonical,
                        raw_flags=raw_flags,
                        paper_size=snap.paper_size,
                    )
                    self._tracked[key] = tracked
                    logger.info(
                        "New print job detected: printer=%s id=%s user=%s doc=%r pages=%s",
                        snap.printer_name,
                        snap.job_id,
                        snap.username,
                        snap.document_name,
                        snap.pages,
                    )
                    self._emit(tracked, status="queued", completed_at=None)
                else:
                    tracked.pages = max(tracked.pages, snap.pages or 0)
                    tracked.size_bytes = max(tracked.size_bytes or 0, snap.size_bytes or 0)
                    tracked.document_name = snap.document_name or tracked.document_name
                    tracked.username = snap.username or tracked.username
                    tracked.last_seen_at = now
                    if canonical != tracked.last_status and canonical != "queued":
                        tracked.last_status = canonical
                        tracked.raw_flags = raw_flags
                        logger.info(
                            "Job %s:%s status=%s flags=%s",
                            snap.printer_name,
                            snap.job_id,
                            canonical,
                            raw_flags,
                        )
                        self._emit(tracked, status=canonical, completed_at=None)

        # 3) Detect jobs that disappeared from the queue (=> finished).
        for key, tracked in list(self._tracked.items()):
            if key in seen_keys:
                continue
            first_missing = self._missing_since.setdefault(key, now)
            grace = (now - first_missing).total_seconds()
            if grace < self.cfg.job_grace_seconds:
                continue

            final_status = "completed"
            if tracked.last_status in {"failed", "cancelled"}:
                final_status = tracked.last_status
            logger.info(
                "Job %s:%s finalised as %s (was %s)",
                tracked.printer_name,
                tracked.job_id,
                final_status,
                tracked.last_status,
            )
            self._emit(tracked, status=final_status, completed_at=now)
            self._tracked.pop(key, None)
            self._missing_since.pop(key, None)

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------
    def _emit(
        self,
        tracked: TrackedJob,
        *,
        status: str,
        completed_at: Optional[datetime],
    ) -> None:
        port = self._printer_ports.get(tracked.printer_name)
        printer_ip = _port_to_ip(port) or self.cfg.expected_printer_ip
        payload = tracked.to_payload(
            status=status,
            completed_at=completed_at,
            extra={"printer_ip": printer_ip},
        )
        try:
            self.on_event(payload)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("on_event handler raised: %s", exc)
