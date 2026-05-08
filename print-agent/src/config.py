"""
Print-agent runtime configuration.

The agent loads configuration from (in order of precedence):

1. Environment variables (e.g. ``PRINT_AGENT_API_BASE_URL``).
2. A YAML config file (default: ``config.yaml`` next to the executable).
3. Built-in defaults.

This makes the agent equally easy to run as a stand-alone script, a
PyInstaller-built EXE, or a Windows service.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

ENV_PREFIX = "PRINT_AGENT_"


def _get_app_dir() -> Path:
    """Return the directory containing the executable / script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


@dataclass
class AgentConfig:
    """Strongly-typed configuration for the print-tracking agent."""

    # ---- Backend ----
    api_base_url: str = "http://localhost:8000/api"
    api_key: str = "change-me-agent-api-key"
    api_timeout_seconds: float = 15.0
    verify_ssl: bool = True

    # ---- Polling ----
    poll_interval_seconds: float = 1.5
    job_grace_seconds: float = 4.0  # how long to wait after a job disappears before flushing
    completion_max_age_seconds: float = 24 * 3600

    # ---- Office printer (informational defaults) ----
    expected_printer_name: Optional[str] = "HP Smart Tank 660-670 series"
    expected_printer_ip: Optional[str] = "192.168.1.131"
    expected_network: Optional[str] = "CKP_WSPACE"

    # ---- Filtering ----
    # Optional whitelist - if set, only jobs targeting these printers are reported.
    printer_whitelist: List[str] = field(default_factory=list)

    # ---- Storage / queue ----
    queue_db_path: str = "agent_offline_queue.sqlite3"
    queue_max_age_days: int = 14
    queue_flush_interval_seconds: float = 30.0
    queue_batch_size: int = 25

    # ---- Logging ----
    log_dir: str = "logs"
    log_level: str = "INFO"
    log_file_max_bytes: int = 5 * 1024 * 1024
    log_file_backup_count: int = 5

    # ---- Service ----
    service_name: str = "PrintTrackingAgent"
    service_display_name: str = "Print Tracking Agent"
    service_description: str = (
        "Monitors the Windows print spooler and forwards print jobs to the "
        "Print Tracking backend."
    )

    # ---- Bookkeeping ----
    config_path: Optional[str] = None

    @property
    def app_dir(self) -> Path:
        return _get_app_dir()

    @property
    def absolute_queue_db(self) -> Path:
        path = Path(self.queue_db_path)
        return path if path.is_absolute() else self.app_dir / path

    @property
    def absolute_log_dir(self) -> Path:
        path = Path(self.log_dir)
        return path if path.is_absolute() else self.app_dir / path

    @property
    def print_log_endpoint(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/print-log"


def _coerce(value: str, target_type: type):
    """Best-effort string -> typed value conversion for env/yaml inputs."""
    if value is None:
        return None
    if target_type is bool:
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is list or target_type is List[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return [v.strip() for v in str(value).split(",") if v.strip()]
    return str(value)


def _load_yaml(path: Path) -> dict:
    """Load a YAML or .env-style config file into a dict.

    Avoids requiring PyYAML by parsing simple ``key: value`` pairs and
    ``key = value`` lines. For complex configs, install PyYAML.
    """
    data: dict = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return data

    try:
        import yaml  # type: ignore
        loaded = yaml.safe_load(text) or {}
        if isinstance(loaded, dict):
            return loaded
    except ImportError:
        pass

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
        elif "=" in line:
            key, _, val = line.partition("=")
        else:
            continue
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            data[key] = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
        else:
            data[key] = val
    return data


def load_config(config_file: Optional[str] = None) -> AgentConfig:
    """Build an AgentConfig from defaults, a YAML file and environment vars."""
    cfg = AgentConfig()

    candidate_paths: List[Path] = []
    if config_file:
        candidate_paths.append(Path(config_file))
    candidate_paths.extend(
        [
            cfg.app_dir / "config.yaml",
            cfg.app_dir / "config.yml",
            cfg.app_dir / "agent.yaml",
        ]
    )

    chosen_path: Optional[Path] = None
    for p in candidate_paths:
        if p and p.is_file():
            chosen_path = p
            break

    if chosen_path:
        cfg.config_path = str(chosen_path)
        for key, value in _load_yaml(chosen_path).items():
            if hasattr(cfg, key):
                annotation = type(getattr(cfg, key)) if getattr(cfg, key) is not None else str
                try:
                    setattr(cfg, key, _coerce(value, annotation))
                except Exception:  # pragma: no cover - defensive
                    setattr(cfg, key, value)

    # Environment variables override file values.
    for field_name in cfg.__dataclass_fields__.keys():
        env_key = f"{ENV_PREFIX}{field_name.upper()}"
        if env_key in os.environ:
            current = getattr(cfg, field_name)
            annotation = type(current) if current is not None else str
            try:
                setattr(cfg, field_name, _coerce(os.environ[env_key], annotation))
            except Exception:  # pragma: no cover - defensive
                setattr(cfg, field_name, os.environ[env_key])

    return cfg
