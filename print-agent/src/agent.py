"""
Print Tracking Agent — main coordinator.

Responsibilities
----------------
* Boot logging + load config
* Spin up the spooler monitor in its own thread
* Spin up an HTTP-flusher thread that drains the offline queue
* Hand each new print event to the API client; on failure persist to SQLite
* Honour graceful shutdown signals (SIGINT/SIGTERM) and Windows service stop

Run modes
---------
* ``python -m print-agent.src.agent``      -> foreground console (dev)
* ``python service/windows_service.py``    -> Windows service wrapper
* ``PrintTrackingAgent.exe`` (PyInstaller) -> stand-alone binary
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from typing import Optional

from .api_client import FatalApiError, PrintApiClient, RetryableApiError
from .config import AgentConfig, load_config
from .logger import configure_logging
from .offline_queue import OfflineQueue
from .spooler_monitor import SpoolerMonitor
from .system_info import get_host_info

logger = logging.getLogger(__name__)


class PrintTrackingAgent:
    """Orchestrates spooler monitoring, queue drainage, and API delivery."""

    def __init__(self, cfg: AgentConfig) -> None:
        self.cfg = cfg
        self.api = PrintApiClient(cfg)
        self.queue = OfflineQueue(cfg.absolute_queue_db, cfg.queue_max_age_days)
        self.monitor = SpoolerMonitor(cfg, on_event=self._handle_event)
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        host = get_host_info()
        logger.info(
            "Print Tracking Agent v1.0 starting | host=%s user=%s ip=%s | api=%s",
            host.computer_name,
            host.username,
            host.primary_ip,
            self.cfg.api_base_url,
        )
        if self.cfg.api_key.startswith("change-me"):
            logger.error(
                "AGENT_API_KEY is using a default placeholder. Configure a "
                "real API key matching the backend before going live."
            )

        self._spawn_thread(target=self._monitor_loop, name="spooler-monitor")
        self._spawn_thread(target=self._flusher_loop, name="queue-flusher")

    def stop(self) -> None:
        if self._stop_event.is_set():
            return
        logger.info("Stopping Print Tracking Agent...")
        self._stop_event.set()
        self.monitor.stop()
        for t in self._threads:
            t.join(timeout=10)
        logger.info("Print Tracking Agent stopped.")

    def wait(self) -> None:
        try:
            while not self._stop_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _spawn_thread(self, target, name: str) -> None:
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        self._threads.append(t)

    def _monitor_loop(self) -> None:
        try:
            self.monitor.run_forever()
        except Exception:
            logger.exception("Spooler monitor crashed.")
            self._stop_event.set()

    def _handle_event(self, payload: dict) -> None:
        """Called by the spooler monitor for each new/updated/finished job."""
        try:
            self.api.submit(payload)
            logger.debug(
                "Submitted print event live: status=%s doc=%r",
                payload.get("status"),
                payload.get("document_name"),
            )
        except FatalApiError as exc:
            logger.error("Dropping payload due to fatal API error: %s", exc)
        except RetryableApiError as exc:
            logger.warning(
                "API unavailable (%s); buffering job locally for retry. doc=%r",
                exc,
                payload.get("document_name"),
            )
            self.queue.enqueue(payload)
        except Exception:
            logger.exception("Unhandled error while submitting print event; buffering.")
            self.queue.enqueue(payload)

    def _flusher_loop(self) -> None:
        """Drains the offline queue continuously until stop_event is set."""
        backoff = self.cfg.queue_flush_interval_seconds
        while not self._stop_event.is_set():
            try:
                self._flush_once()
            except Exception:  # pragma: no cover - defensive
                logger.exception("Queue flush iteration failed")
            self._stop_event.wait(timeout=backoff)

        # Final flush attempt at shutdown.
        try:
            self._flush_once(final=True)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Final queue flush failed.")

    def _flush_once(self, final: bool = False) -> None:
        purged = self.queue.purge_old()
        if purged:
            logger.warning("Purged %s offline-queue rows older than %s days.", purged, self.cfg.queue_max_age_days)

        batch = self.queue.fetch_batch(limit=self.cfg.queue_batch_size)
        if not batch:
            return

        logger.info("Flushing %s buffered print event(s) to backend...", len(batch))
        successes: list[int] = []
        for row_id, payload in batch:
            try:
                self.api.submit(payload)
                successes.append(row_id)
            except FatalApiError as exc:
                logger.error(
                    "Buffered row %s rejected fatally: %s; deleting.", row_id, exc
                )
                successes.append(row_id)  # Drop the row.
            except RetryableApiError as exc:
                self.queue.mark_failed(row_id, str(exc), retry_in_seconds=60)
                if not final:
                    break  # Backend is unreachable; stop hammering it.
            except Exception as exc:  # pragma: no cover - defensive
                self.queue.mark_failed(row_id, str(exc), retry_in_seconds=60)
                if not final:
                    break

        if successes:
            self.queue.mark_succeeded(successes)
            logger.info("Drained %s row(s) successfully.", len(successes))


# ---------------------------------------------------------------------------
# Console entrypoint
# ---------------------------------------------------------------------------
def _install_signal_handlers(agent: PrintTrackingAgent) -> None:
    def _handler(signum, _frame):
        logger.info("Received signal %s, shutting down.", signum)
        agent.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            # Some signals are unsupported on Windows / non-main threads.
            pass


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="print-agent",
        description="Print Tracking Agent — Windows print spooler watcher.",
    )
    parser.add_argument("--config", "-c", help="Path to config.yaml override.")
    parser.add_argument("--once", action="store_true", help="Run a single poll then exit (debug only).")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    configure_logging(cfg)

    agent = PrintTrackingAgent(cfg)
    _install_signal_handlers(agent)
    agent.start()

    if args.once:
        time.sleep(max(cfg.poll_interval_seconds * 3, 5))
        agent.stop()
        return 0

    agent.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
