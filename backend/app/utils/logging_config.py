"""Centralised logging configuration."""

from __future__ import annotations

import logging
import sys

from ..config import settings


def configure_logging() -> None:
    """Configure the root logger with a sensible production-friendly format."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Tame noisy 3rd-party loggers in production.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if settings.is_production else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
