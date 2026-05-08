"""Cached host information (computer name, current user, primary LAN IP)."""

from __future__ import annotations

import getpass
import logging
import os
import socket
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HostInfo:
    computer_name: str
    username: str
    primary_ip: Optional[str]


def _detect_primary_ip() -> Optional[str]:
    """Find the LAN IP used to reach the default route (no actual packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 8.8.8.8 used only to pick the routing interface; UDP send isn't actually performed.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None
    finally:
        s.close()


@lru_cache(maxsize=1)
def get_host_info() -> HostInfo:
    """Return cached identity info for the current host."""
    try:
        username = os.environ.get("USERNAME") or getpass.getuser()
    except Exception:
        username = "unknown"
    try:
        computer = os.environ.get("COMPUTERNAME") or socket.gethostname()
    except Exception:
        computer = "unknown"
    return HostInfo(
        computer_name=computer,
        username=username,
        primary_ip=_detect_primary_ip(),
    )
