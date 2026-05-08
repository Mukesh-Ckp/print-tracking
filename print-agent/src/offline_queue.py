"""
Offline queue: durable, crash-safe SQLite buffer for print events.

Whenever a print event cannot be delivered to the backend (network loss,
backend redeploy, transient 5xx, etc.) we write it to a local SQLite
database and retry it later. This guarantees zero data loss even across
machine restarts.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OfflineQueue:
    """Thread-safe SQLite-backed FIFO queue for print event payloads."""

    def __init__(self, db_path: Path, max_age_days: int = 14) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_age_days = max_age_days
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_json  TEXT NOT NULL,
                    attempts      INTEGER NOT NULL DEFAULT 0,
                    last_error    TEXT,
                    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                    next_attempt  TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_pending_next_attempt ON pending(next_attempt);")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enqueue(self, payload: dict) -> int:
        """Persist a payload and return its row id."""
        body = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO pending (payload_json) VALUES (?);",
                (body,),
            )
            return int(cur.lastrowid or 0)

    def fetch_batch(self, limit: int) -> List[Tuple[int, dict]]:
        """Return up to ``limit`` due rows."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, payload_json
                FROM pending
                WHERE next_attempt <= datetime('now')
                ORDER BY id ASC
                LIMIT ?;
                """,
                (limit,),
            ).fetchall()
            results: List[Tuple[int, dict]] = []
            for row in rows:
                try:
                    payload = json.loads(row["payload_json"])
                except json.JSONDecodeError:
                    logger.exception("Corrupt queue row id=%s, deleting", row["id"])
                    conn.execute("DELETE FROM pending WHERE id = ?;", (row["id"],))
                    continue
                results.append((int(row["id"]), payload))
            return results

    def mark_succeeded(self, ids: Iterable[int]) -> None:
        ids = list(ids)
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        with self._lock, self._connect() as conn:
            conn.execute(f"DELETE FROM pending WHERE id IN ({placeholders});", ids)

    def mark_failed(self, row_id: int, error: str, retry_in_seconds: int) -> None:
        next_attempt = (datetime.now(timezone.utc) + timedelta(seconds=retry_in_seconds)).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE pending
                SET attempts = attempts + 1,
                    last_error = ?,
                    next_attempt = ?
                WHERE id = ?;
                """,
                (error[:1000], next_attempt, row_id),
            )

    def purge_old(self) -> int:
        """Remove entries older than ``max_age_days``. Returns number deleted."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.max_age_days)).isoformat()
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM pending WHERE created_at < ?;", (cutoff,))
            return cur.rowcount or 0

    def size(self) -> int:
        with self._lock, self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM pending;").fetchone()[0])
