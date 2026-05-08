# Architecture

Detailed view of the components, threads, and data flow.

## Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Office network                            │
│                                                                     │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│   │  Laptop A  │  │  Laptop B  │  │  Laptop C  │  │  Laptop D  │    │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘    │
│         │ \\MAIN-PC\HP Smart Tank ...                                │
│         └─────────────┬─────────────────┴─────────────────┘          │
│                       ▼                                              │
│              ┌────────────────┐         ┌─────────────────────┐      │
│              │ Main Office PC │  → IP → │ HP Smart Tank 660   │      │
│              │ (Windows host) │         │  192.168.1.131      │      │
│              │                │         └─────────────────────┘      │
│              │ ┌─────────────┐│                                      │
│              │ │ print-agent ││                                      │
│              │ │  (service)  ││                                      │
│              │ └──────┬──────┘│                                      │
│              └────────┼───────┘                                      │
└───────────────────────┼──────────────────────────────────────────────┘
                        │ HTTPS, X-API-Key
                        ▼
              ┌─────────────────────┐
              │  FastAPI Backend    │
              │  (Render)           │
              │                     │
              │  /api/print-log     │  ← agent ingestion
              │  /api/auth/login    │
              │  /api/dashboard     │
              │  /api/prints        │
              │  /api/stats         │
              │  /api/reports/*     │
              └──────────┬──────────┘
                         │ SQL
                         ▼
              ┌─────────────────────┐
              │  PostgreSQL (Neon)  │
              │   admins            │
              │   print_logs        │
              │   printers          │
              │   activity_logs     │
              └──────────┬──────────┘
                         ▲
                         │ HTTPS, JWT
                         │
              ┌──────────┴──────────┐
              │  React Dashboard    │
              │  (Vercel)           │
              │                     │
              │  Login              │
              │  Dashboard          │
              │  Print Logs         │
              │  Analytics          │
              │  Reports            │
              │  Settings           │
              └─────────────────────┘
```

## Print agent — internal threads

```
┌──────────────────────────────────────────────────┐
│  PrintTrackingAgent process                      │
│                                                  │
│  ┌────────────────┐    ┌──────────────────────┐  │
│  │ spooler-monitor│    │ queue-flusher        │  │
│  │ (1 thread)     │    │ (1 thread)           │  │
│  │                │    │                      │  │
│  │ poll EnumJobs  │    │ drain SQLite buffer  │  │
│  │ every 1.5s     │    │ every 30s            │  │
│  └─────┬──────────┘    └─────┬────────────────┘  │
│        │ on_event              │ batch POST       │
│        ▼                        ▼                 │
│  ┌────────────────────────────────────────────┐  │
│  │  PrintApiClient (requests.Session)         │  │
│  │  - retries, error classification           │  │
│  │  - X-API-Key header                        │  │
│  └─────┬──────────────────────────────────────┘  │
│        │ on retryable failure                     │
│        ▼                                          │
│  ┌────────────────────────────────────────────┐  │
│  │  OfflineQueue (SQLite WAL)                 │  │
│  │  - INSERT pending(payload_json)            │  │
│  │  - DELETE on success                       │  │
│  │  - exponential backoff via next_attempt    │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

* The **spooler monitor** uses `win32print.EnumJobs` on every printer
  visible to the Windows session. Jobs are tracked by `(printer_name,
  job_id)` between ticks. When a previously-seen job disappears for
  longer than `job_grace_seconds`, it's considered finished.
* Status flags from `JOB_INFO_2.Status` are decoded into canonical
  statuses (`queued`, `printing`, `paused`, `completed`, `failed`,
  `cancelled`, `unknown`).
* **Idempotent emission**: each transition emits one event:
  `queued → printing → completed/failed/cancelled`. Duplicate
  POSTs are harmless because the backend stores them as separate
  rows; the dashboard groups by `job_id` for analytics.
* **Resilience**: every uncaught exception in either thread is logged
  but never propagates beyond the thread, so the agent stays up.

## Backend internals

```
HTTP → CORSMiddleware → RequestLoggingMiddleware →
       FastAPI router → endpoint function → SQLAlchemy session
                                            │
                                            ▼
                                   service layer (services/)
                                            │
                                            ▼
                                   ORM models (models/)
                                            │
                                            ▼
                                   PostgreSQL / SQLite
```

* **Lifespan** (`app/main.py`): runs `init_db()` then seeds the
  default admin and printer. Both seeds are idempotent.
* **Auth**:
  * `OAuth2PasswordBearer` for the dashboard JWT.
  * `Header("X-API-Key")` + `secrets.compare_digest` for the agent.
* **Pagination**: `/api/prints` enforces `1 ≤ page_size ≤ 200`.
  Reports use a separate `export_print_logs` helper capped at 5,000
  rows to avoid memory blowups.
* **Stats**: hourly + daily time series are computed in pure Python
  after a single SELECT to avoid dialect-specific date_trunc syntax.
* **Reports**:
  * Excel via `openpyxl` with header styling and frozen header row.
  * PDF via `reportlab` (landscape A4, alternating row backgrounds).
* **Activity log**: writes are best-effort; failures are logged but
  never break the parent request.

## Database schema

| Table | Purpose | Indexes |
|---|---|---|
| `admins` | Dashboard users | unique on `username`, `email` |
| `printers` | Known printer registry | unique on `name`, indexed on `ip_address` |
| `print_logs` | One row per detected job | composite indexes on `(received_at, status)`, `(username, received_at)`, `(printer_name, received_at)` |
| `activity_logs` | Audit trail | indexed on `actor`, `action`, `created_at` |

`PrintLog.status` is a Python `enum.Enum` stored as a string
(non-native enum) for cross-database portability (Postgres, SQLite,
MySQL all just see it as `VARCHAR(32)`).

## Frontend internals

* **State**: `AuthContext` keeps the JWT and admin profile in
  `localStorage`. The Axios interceptor automatically attaches the
  token and on 401 it clears storage + redirects to `/login`.
* **Routing**: top-level `BrowserRouter`, all dashboard routes are
  wrapped in `ProtectedRoute → Layout` which shows the sidebar +
  header.
* **Polling**: Dashboard refreshes every 15 s; Print Logs every 20 s
  when "Auto-refresh" is enabled.
* **Charts**: Chart.js (`react-chartjs-2`). All four chart types
  share a `baseChartOptions` object configured for the dark theme.
* **Reports**: client downloads the file as a Blob via Axios with
  `responseType: 'blob'` and triggers a download via a hidden `<a>`.

## Why polling and not the spooler change-notification API?

The Win32 `FindFirstPrinterChangeNotification` API requires either
admin/SYSTEM rights or running inside the spooler service context.
Both options are fragile to ship to customer machines. Polling
`EnumJobs` every ~1.5 s costs <1 ms per call and reliably captures
every job, including very brief ones (the spooler keeps each job
visible for at least one polling cycle). This trade-off favours
operational simplicity over a few hundred bytes of saved network
chatter per second.
