# Setup Guide

This document walks you through bringing up the complete Print Tracking
System on a fresh machine.

There are three components, each with its own folder and README:

| Component | Folder | Where it normally runs |
|---|---|---|
| Backend (FastAPI) | `backend/` | Render |
| Frontend (React) | `frontend/` | Vercel |
| Print agent | `print-agent/` | Main Office PC (the PC sharing the printer) |

For convenience, this guide covers running everything **locally** on
one Windows machine first. For production deployment see
[`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## Prerequisites

* **Python 3.10+** (3.12 recommended)
* **Node.js 18+** and **npm**
* **Windows 10/11** for the print agent
* The shared **HP Smart Tank 660-670 series** printer reachable as
  `192.168.1.131` on `CKP_WSPACE`
* Admin/CEO laptop with a modern browser (Chrome / Edge)

Optional for production:

* GitHub account
* [Neon](https://neon.tech) PostgreSQL account
* [Render](https://render.com) account
* [Vercel](https://vercel.com) account

---

## 1. Backend — local

```powershell
cd backend

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
notepad .env
```

Generate strong secrets and paste them into `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"   # -> JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"   # -> AGENT_API_KEY
```

Run the server:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
... | Database tables ensured (create_all complete).
... | Bootstrap admin created with username=admin. PLEASE CHANGE THE DEFAULT PASSWORD IMMEDIATELY.
... | Registered default printer: HP Smart Tank 660-670 series
... | Application ready and accepting traffic.
```

Test it:

* Health: <http://localhost:8000/health>
* API docs: <http://localhost:8000/docs>

The default admin credentials seeded from `.env` are
`admin / Admin@123`. **Change them immediately.**

---

## 2. Frontend — local

```powershell
cd frontend
copy .env.example .env
# Edit .env: VITE_API_BASE_URL=http://localhost:8000/api

npm install
npm run dev
```

Open <http://localhost:5173>, log in with the bootstrap admin.
You'll land on the Dashboard. Until the agent posts data, the cards
will all show 0.

To verify the dashboard wiring, you can post a synthetic print log:

```powershell
$key = "<your AGENT_API_KEY>"
$body = @{
  username = "alice"
  computer_name = "ALICE-PC"
  laptop_ip = "192.168.1.40"
  printer_name = "HP Smart Tank 660-670 series"
  printer_ip = "192.168.1.131"
  document_name = "test.pdf"
  pages = 3
  copies = 1
  total_pages = 3
  status = "completed"
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/print-log" `
  -Headers @{ "X-API-Key" = $key } `
  -ContentType "application/json" -Body $body
```

The dashboard auto-refreshes every 15 s and you'll see the new entry
plus a "1 new print received" toast.

---

## 3. Print agent — main office PC

> The print-agent must run on the same PC that shares the printer to
> the rest of the office (i.e. the host of the Windows print queue).
> User laptops do NOT need anything installed.

```powershell
cd print-agent

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy config.example.yaml config.yaml
notepad config.yaml
```

In `config.yaml`, set:

```yaml
api_base_url: http://localhost:8000/api    # or your Render URL in production
api_key: <paste backend AGENT_API_KEY>
poll_interval_seconds: 1.5
```

Run it in the foreground for testing:

```powershell
py -m src.agent
```

Print anything from any office laptop. Within ~2 seconds the agent
prints `New print job detected` to its log and POSTs the job to the
backend. The dashboard auto-refreshes and you'll see the live entry.

When you're confident it's working, install it as a Windows service
(see next section).

---

## 4. Run the print agent as a Windows service

Open **Command Prompt as Administrator**:

```powershell
cd print-agent
service\install_service.bat
```

This will:

1. Create a venv inside `print-agent\.venv` if one doesn't exist.
2. Install `requirements.txt`.
3. Run `python -m pywin32_postinstall -install`.
4. Register the `PrintTrackingAgent` Windows service with auto-start.
5. Start it.

Verify:

```powershell
sc query PrintTrackingAgent
```

Expected output: `STATE: 4 RUNNING`.

Logs are written to `print-agent\logs\print_agent.log` (rotated at 5 MB
with 5 backups).

To stop / remove:

```powershell
service\uninstall_service.bat
```

To rotate the API key, edit `config.yaml` and restart the service:

```powershell
sc stop PrintTrackingAgent
sc start PrintTrackingAgent
```

---

## 5. Alternative: build a stand-alone EXE

If you prefer not to use a Windows service, you can produce a single
executable and register it with Task Scheduler:

```powershell
cd print-agent
build\build_exe.bat
# creates dist\PrintTrackingAgent.exe

startup\register_startup.bat
# registers a "PrintTrackingAgent" Scheduled Task that runs at user logon
```

This approach is simpler when the office PC always logs in as the same
user and `pywin32_postinstall` causes friction.

---

## 6. Smoke test the whole stack

1. Open the dashboard.
2. From any office laptop, print any document to
   `\\MAIN-PC\HP Smart Tank 660-670 series`.
3. The agent on the Main Office PC detects the job and POSTs it.
4. Within 15 s the dashboard updates with:
   * Toast: "1 new print received"
   * KPI counters increment
   * Recent prints table shows the new row
   * Hourly chart bar grows

If any of these don't happen, see the Troubleshooting section in
[`print-agent/README.md`](../print-agent/README.md).
