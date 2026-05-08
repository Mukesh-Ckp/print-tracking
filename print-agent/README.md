# Print Tracking — Windows Print Agent

Background service that runs on the **Main Office PC** (the one that
shares the HP Smart Tank 660-670 to the rest of the office). It watches
the Windows print spooler in real-time and forwards every print job to
the Print Tracking backend.

* **No installation on user laptops.** All laptops keep printing
  through the shared printer as usual; the queue lives on this PC, so
  observing the queue here captures every job.
* **Works offline:** events that cannot be delivered are persisted to a
  local SQLite buffer and flushed automatically once connectivity is
  restored.
* **Survives reboots:** can run as a Windows service or as a Scheduled
  Task that auto-starts on logon.

---

## Architecture

```
Office Laptops
      |
      |  print to \\MainPC\HP Smart Tank...
      v
Main Office PC  (this agent runs here)
      |
      |  win32print.EnumJobs(...) every ~1.5s
      |
      |  POST /api/print-log  (X-API-Key)
      v
FastAPI backend on Render -> Neon PostgreSQL
```

---

## Files

| Path | Purpose |
|---|---|
| `src/agent.py` | Coordinator (boots, threads, signal handlers) |
| `src/spooler_monitor.py` | Polls the spooler and tracks each job |
| `src/api_client.py` | HTTP client (retries, error classification) |
| `src/offline_queue.py` | Crash-safe SQLite buffer of unsent events |
| `src/system_info.py` | Cached host / user / IP info |
| `src/config.py` | YAML + env loader |
| `src/logger.py` | Rotating file + console logging |
| `service/windows_service.py` | Installable Windows service |
| `service/install_service.bat` | One-shot installer for the service |
| `service/uninstall_service.bat` | Stops + removes the service |
| `build/agent.spec` | PyInstaller spec to build the EXE |
| `build/build_exe.bat` | Builds `dist/PrintTrackingAgent.exe` |
| `startup/register_startup.bat` | Registers Scheduled Task auto-start |
| `startup/unregister_startup.bat` | Removes that task |
| `config.example.yaml` | Sample runtime configuration |

---

## Quickstart (development)

```powershell
cd print-agent

py -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy config.example.yaml config.yaml
notepad config.yaml   # set api_base_url and api_key

py -m src.agent
```

You should see lines like:

```
Print Tracking Agent v1.0 starting | host=MAIN-PC user=admin ip=192.168.1.20 ...
Spooler monitor starting; poll_interval=1.50s
```

Now print something from any office laptop. Within ~2 seconds you'll
see the agent log a `New print job detected` line, the backend will
receive a `POST /api/print-log`, and the React dashboard will refresh
to show the new event.

---

## Configuration

The agent reads (in order of priority):

1. **Environment variables** prefixed with `PRINT_AGENT_` — useful when
   running as a service.
2. **`config.yaml`** next to the executable / script.
3. **Built-in defaults** in `src/config.py`.

The most important keys:

```yaml
api_base_url: https://your-backend.onrender.com/api
api_key: REPLACE-WITH-AGENT-API-KEY     # MUST match backend AGENT_API_KEY
poll_interval_seconds: 1.5
printer_whitelist: []                   # [] = track all printers
```

---

## Run as a Windows Service (recommended for production)

Open **Command Prompt as Administrator**:

```powershell
cd print-agent
service\install_service.bat
```

The installer creates a venv, installs dependencies, runs the
`pywin32_postinstall` step, registers the service with auto-start,
and starts it.

Verify:

```powershell
sc query PrintTrackingAgent
```

To stop / remove:

```powershell
service\uninstall_service.bat
```

Logs are written to `print-agent\logs\print_agent.log` (rotated at 5 MB).

---

## Run as an EXE + Scheduled Task (alternative)

```powershell
cd print-agent
build\build_exe.bat
# creates dist\PrintTrackingAgent.exe

startup\register_startup.bat
# registers a per-user Scheduled Task that runs at logon (RUN AS ADMIN)
```

This avoids the pywin32 service permissions and works well if the
office PC always logs in as a fixed user.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Authentication rejected (401)` in logs | `api_key` does not match backend `AGENT_API_KEY`. |
| `Connection error` / `Timeout` | Backend down or firewalled. Events are buffered in SQLite and resent automatically. |
| No jobs detected | Confirm the printer is actually shared from this PC (the queue must live here). Check `printer_whitelist` if set. |
| Service won't start | Run `python -m pywin32_postinstall -install` once as administrator. |
| Agent not running after reboot | Service startup type must be `Automatic` (`sc config PrintTrackingAgent start= auto`). |
