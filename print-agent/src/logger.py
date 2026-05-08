"""Logging setup for the print-agent (rotating file + console)."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import AgentConfig


def configure_logging(cfg: AgentConfig) -> logging.Logger:
    """Configure root logger; returns the agent's logger."""
    log_dir = cfg.absolute_log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "print_agent.log"

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=cfg.log_file_max_bytes,
        backupCount=cfg.log_file_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    level = getattr(logging, cfg.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    # Replace any pre-existing handlers (e.g. when re-loaded as a service).
    root.handlers = [file_handler, console_handler]

    return logging.getLogger("print_agent")
