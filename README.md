# Enterprise Print Tracking & Monitoring System

Production-ready, enterprise-grade software that captures **every print
job** sent to your office's shared printer and surfaces it in a beautiful
React admin dashboard for the CEO/admin team to monitor in real-time.

> **Office context that this system was built for**
>
> * Office shares a single **HP Smart Tank 660-670 series** printer
>   (IP `192.168.1.131`) over the **CKP_WSPACE** WiFi network.
> * Multiple laptops print to it via a Windows shared queue hosted on
>   the **Main Office PC**.
> * Users print **without permission prompts**; tracking is silent.
> * Admin/CEO opens a web dashboard from anywhere to see live activity,
>   historical logs, analytics, and exportable reports.

---

## High-level architecture

```
+----------------+      +----------------+      +-------------------------+
|  Office laptop |      |  Office laptop |      |  Office laptop          |
|  (any user)    |      |  (any user)    |      |  (any user)             |
+--------+-------+      +--------+-------+      +------------+------------+
         \\                       |                           //
          \\         print to shared queue \\\\MAIN-PC\\HP...
           \\                      |                          //
            +---------+------------+--------------------------+
                      |
              +-------v---------+
              | Main Office PC  |   Windows shared printer host
              |                 |   ----------------------------
              | print-agent     |   - Polls Windows spooler
              | (Python service)|   - Captures every job
              |                 |   - Stores offline queue (SQLite)
              +-------+---------+
                      |  HTTPS POST /api/print-log  (X-API-Key)
                      v
        +-------------+--------------+
        |  FastAPI Backend (Render)  |
        |  - JWT auth                |
        |  - REST APIs               |
        |  - PDF/Excel reports       |
        +-------------+--------------+
                      |
                      v
           +----------+-----------+
           |  PostgreSQL (Neon)   |
           +----------+-----------+
                      ^
                      |  HTTPS REST + JWT
                      |
            +---------+----------+
            |  React Dashboard   |   (Vercel)
            |  - Live monitoring |
            |  - Charts          |
            |  - Reports         |
            +--------------------+
```

The system is split into **three independent components**:

| Folder        | What it is                                            | Where it runs                    |
|---------------|-------------------------------------------------------|----------------------------------|
| `backend/`    | FastAPI service + PostgreSQL ORM                      | Render (cloud)                   |
| `frontend/`   | React + Vite admin dashboard                          | Vercel (cloud)                   |
| `print-agent/`| Python Windows service watching the print spooler     | Main Office PC (on-premise)      |

See per-folder `README.md` files for component-specific instructions.
The full deployment + setup walkthrough lives in [`docs/SETUP.md`](docs/SETUP.md)
and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## What admins see

The dashboard auto-loads on each login and auto-refreshes every 15 s.

* **Dashboard** — KPI cards (today / this month / all-time), hourly
  activity chart, status breakdown, top users, top printers, last 30
  days bar chart, and a live "Recent Prints" table.
* **Print Logs** — searchable, filterable, paginated table with
  username / computer / printer / status / date filters and Excel/PDF
  export buttons that respect current filters.
* **Analytics** — 30-day trend lines, top users, status mix, printer
  utilisation.
* **Reports** — quick PDF/Excel export with date-range presets.
* **Settings** — account info, registered printers, agent guidance.

Everything is responsive and uses a modern dark enterprise theme.

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 18, Vite 5, React Router 6, Axios, Chart.js |
| Backend | FastAPI 0.115, SQLAlchemy 2, Pydantic 2, Gunicorn + Uvicorn |
| Auth | JWT (HS256, python-jose) + bcrypt + static API key for agent |
| DB | PostgreSQL (Neon) — falls back to SQLite locally |
| Reports | openpyxl (Excel) + reportlab (PDF) |
| Print agent | Python 3.10+, pywin32, win32print, WMI, requests |
| Persistence in agent | SQLite (`agent_offline_queue.sqlite3`) |
| Service | pywin32 service wrapper + PyInstaller EXE + Task Scheduler |
| Hosting | Backend → Render, Frontend → Vercel, DB → Neon |

---

## Repository layout

```
print-tracking-system/
├── backend/                 # FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database/        # SQLAlchemy engine + Base
│   │   ├── models/          # admins, print_logs, printers, activity_logs
│   │   ├── schemas/         # Pydantic models
│   │   ├── auth/            # JWT + API-key + password hashing
│   │   ├── middleware/      # request logging
│   │   ├── routers/         # auth, prints, dashboard, stats, reports
│   │   ├── services/        # business logic, exports, stats
│   │   └── utils/           # logging config, seeding
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── render.yaml
│   ├── start.sh
│   └── .env.example
├── frontend/                # React + Vite dashboard
│   ├── src/
│   │   ├── api/             # axios client + endpoint wrappers
│   │   ├── context/         # AuthContext
│   │   ├── components/      # Layout, Sidebar, Header, StatCard, …
│   │   ├── pages/           # Login, Dashboard, PrintLogs, Reports, Analytics, Settings
│   │   ├── styles/          # global.css (design tokens + components)
│   │   └── utils/           # formatting helpers
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json
│   └── .env.example
├── print-agent/             # Windows print-tracking agent
│   ├── src/                 # agent.py, spooler_monitor.py, api_client.py, …
│   ├── service/             # windows_service.py + install/uninstall .bat
│   ├── build/               # agent.spec + build_exe.bat
│   ├── startup/             # Scheduled Task register/unregister .bat
│   ├── config.example.yaml
│   ├── requirements.txt
│   └── .env.example
└── docs/
    ├── SETUP.md
    ├── DEPLOYMENT.md
    ├── PRINT-SERVER-SETUP.md
    ├── ARCHITECTURE.md
    └── API.md
```

---

## Quickstart (full local stack on a single Windows PC)

> Requires Python 3.10+, Node 18+, and being able to share the office
> printer from this PC.

### 1. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# generate strong secrets
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))" >> .env
python -c "import secrets; print('AGENT_API_KEY='  + secrets.token_urlsafe(48))" >> .env

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A bootstrap admin (`admin` / `Admin@123`) is auto-created. Open
<http://localhost:8000/docs> for the API explorer.

### 2. Frontend

```powershell
cd frontend
copy .env.example .env
# .env -> VITE_API_BASE_URL=http://localhost:8000/api
npm install
npm run dev
# open http://localhost:5173
```

### 3. Print agent

```powershell
cd print-agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config.example.yaml config.yaml

# Edit config.yaml:
#   api_base_url: http://localhost:8000/api
#   api_key:      <copy AGENT_API_KEY from backend .env>

py -m src.agent
```

Print anything from any office laptop. Within ~2 seconds the agent
detects the job, posts it to the backend, and the dashboard updates
automatically.

---

## Production deployment

* **Backend** → Render (Blueprint via `backend/render.yaml`).
* **DB** → Neon Postgres (free tier works for SMB workloads).
* **Frontend** → Vercel (root dir = `frontend`, env var
  `VITE_API_BASE_URL` = your Render URL + `/api`).
* **Agent** → Run as Windows service on the Main Office PC
  (`service/install_service.bat` as administrator).

Step-by-step instructions live in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Security notes

* All admin endpoints require a JWT.
* The print-agent ingestion endpoint requires a long random
  `X-API-Key` matching the backend's `AGENT_API_KEY` (constant-time
  compared). Rotate periodically.
* `bcrypt` for password hashing.
* `CORS_ORIGINS` should be locked down to the Vercel domain in
  production.
* Default admin password **must be changed immediately** after first
  login. Add `DEFAULT_ADMIN_PASSWORD` env var in production with a
  strong value before first deploy.

---

## Behaviour after deployment

* Print logs are persisted in PostgreSQL — they survive restarts and
  redeploys forever.
* When the admin opens the dashboard, the backend reads from the
  database, so all historical activity loads automatically.
* The agent reconnects to the backend automatically after backend
  redeploys / network outages and replays anything it had buffered.
* The agent auto-starts with Windows (service or scheduled task).

---

## Documentation

* [`docs/SETUP.md`](docs/SETUP.md) — full local + production setup walkthrough
* [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Render + Vercel + Neon deployment
* [`docs/PRINT-SERVER-SETUP.md`](docs/PRINT-SERVER-SETUP.md) — one PC shared printer + laptops (no agent on laptops)
* [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, threads, data flow
* [`docs/API.md`](docs/API.md) — REST API reference

---

## License

Internal proprietary software. Replace this section with your
preferred licence (MIT, Apache 2.0, etc.) before open-sourcing.
