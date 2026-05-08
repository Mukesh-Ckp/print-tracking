"""
HTTP client for posting print events to the backend.

Robust to:
* Backend down / unreachable -> raises a retryable exception, payload is
  saved in the offline queue.
* Authentication failures (401/403) -> non-retryable; logs an error and
  drops the row to avoid an infinite retry storm.
* 5xx and connection errors -> retryable.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from .config import AgentConfig

logger = logging.getLogger(__name__)


class PrintApiError(Exception):
    """Base class for backend API errors."""


class RetryableApiError(PrintApiError):
    """Indicates the caller should re-queue this payload."""


class FatalApiError(PrintApiError):
    """Indicates the payload should be dropped (e.g. 4xx other than 408/429)."""


class PrintApiClient:
    def __init__(self, cfg: AgentConfig) -> None:
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": cfg.api_key,
                "Content-Type": "application/json",
                "User-Agent": "PrintTrackingAgent/1.0",
            }
        )

    def submit(self, payload: dict) -> Optional[dict]:
        """Post a single print event. Raises ``PrintApiError`` on failure."""
        url = self.cfg.print_log_endpoint
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.cfg.api_timeout_seconds,
                verify=self.cfg.verify_ssl,
            )
        except requests.Timeout as exc:
            raise RetryableApiError(f"Timeout: {exc}") from exc
        except requests.ConnectionError as exc:
            raise RetryableApiError(f"Connection error: {exc}") from exc
        except requests.RequestException as exc:
            raise RetryableApiError(f"Request error: {exc}") from exc

        if response.status_code in (200, 201, 202):
            try:
                return response.json()
            except ValueError:
                return None

        body = (response.text or "")[:500]
        if response.status_code in (401, 403):
            raise FatalApiError(
                f"Authentication rejected ({response.status_code}). "
                f"Check AGENT_API_KEY. Body: {body}"
            )
        if response.status_code in (400, 422):
            raise FatalApiError(
                f"Bad request ({response.status_code}). Dropping payload. Body: {body}"
            )
        if 500 <= response.status_code < 600 or response.status_code == 429:
            raise RetryableApiError(
                f"Backend transient error {response.status_code}. Body: {body}"
            )
        raise RetryableApiError(
            f"Unexpected status {response.status_code}. Body: {body}"
        )

    def health(self) -> bool:
        """Lightweight reachability check, used for backoff decisions."""
        url = self.cfg.api_base_url.rstrip("/").rsplit("/api", 1)[0] + "/health"
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
