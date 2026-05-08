"""
Windows service wrapper for the Print Tracking Agent.

Usage (run an elevated PowerShell / cmd):

    # Install:
    python service\\windows_service.py install
    # Configure auto-start (so it survives reboots):
    python service\\windows_service.py --startup auto install
    # Start / stop / remove:
    python service\\windows_service.py start
    python service\\windows_service.py stop
    python service\\windows_service.py remove

When running as a frozen EXE produced by PyInstaller, the agent should be
launched in console mode rather than via this service wrapper. For frozen
deployments use the Task Scheduler approach in
``startup/register_startup.bat``.

Requirements:
    pip install pywin32
    python -m pywin32_postinstall -install   (one-time, elevated)
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

# Ensure the package can be imported when the script is run directly
# from the service control manager (which sets cwd to system32).
_THIS_DIR = Path(__file__).resolve().parent
_PKG_ROOT = _THIS_DIR.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

try:
    import servicemanager  # type: ignore
    import win32event  # type: ignore
    import win32service  # type: ignore
    import win32serviceutil  # type: ignore
except ImportError as exc:  # pragma: no cover - depends on environment
    print("pywin32 is required to install the Windows service:", exc)
    sys.exit(2)

from src.agent import PrintTrackingAgent  # noqa: E402
from src.config import load_config  # noqa: E402
from src.logger import configure_logging  # noqa: E402


class PrintTrackingService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PrintTrackingAgent"
    _svc_display_name_ = "Print Tracking Agent"
    _svc_description_ = (
        "Monitors the Windows print spooler and forwards every print job to "
        "the Print Tracking & Monitoring backend (HP Smart Tank shared printer)."
    )

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.agent: PrintTrackingAgent | None = None
        self._wait_thread: threading.Thread | None = None
        # Keep service responsive while the agent runs in background threads.
        os.chdir(str(_PKG_ROOT))

    # ------------------------------------------------------------------
    # Service-control hooks
    # ------------------------------------------------------------------
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        cfg = load_config()
        configure_logging(cfg)
        self.agent = PrintTrackingAgent(cfg)
        self.agent.start()

        # Block until the SCM signals stop.
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.agent is not None:
            self.agent.stop()
        win32event.SetEvent(self.stop_event)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No args -> assume we were started by the Service Control Manager.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PrintTrackingService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PrintTrackingService)
