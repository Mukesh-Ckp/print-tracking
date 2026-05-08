"""Helpers for writing audit-trail entries into the activity_logs table."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(
    db: Session,
    *,
    actor: Optional[str],
    action: str,
    target: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None,
    commit: bool = True,
) -> ActivityLog:
    """Persist a new ActivityLog row. Errors are logged but never raised."""
    entry = ActivityLog(
        actor=actor,
        action=action,
        target=target,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    try:
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to write activity log %s: %s", action, exc)
        db.rollback()
    return entry
