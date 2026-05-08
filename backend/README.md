# Print Tracking — Backend (FastAPI)

REST API for the **Enterprise Print Tracking & Monitoring System**.

* **Framework:** FastAPI + SQLAlchemy 2.0
* **Database:** PostgreSQL (Neon) — falls back to SQLite locally
* **Auth:** JWT (admin dashboard) + static API key (on-premise print-agent)
* **Reports:** Excel (`openpyxl`) and PDF (`reportlab`)

---

## Quickstart (local)

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000/docs> for the interactive Swagger UI.

The first run auto-creates the schema and seeds the bootstrap admin
defined in `.env` (defaults: `admin / Admin@123` — **change immediately**).

---

## Environment variables

See [`.env.example`](./.env.example) for a fully-commented template.
The most important variables for production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon Postgres connection string |
| `JWT_SECRET_KEY` | Long random string for signing admin JWTs |
| `AGENT_API_KEY` | Shared secret presented by the print-agent |
| `DEFAULT_ADMIN_*` | Bootstrap admin credentials |
| `CORS_ORIGINS` | Comma-separated list of allowed dashboard origins |

Generate strong secrets:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## API endpoints

All endpoints are mounted under `/api`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | none | Admin login → JWT |
| `GET`  | `/api/auth/me` | JWT | Current admin |
| `POST` | `/api/print-log` | API key | Ingest a print job (called by agent) |
| `GET`  | `/api/prints` | JWT | Paginated list with filters |
| `GET`  | `/api/prints/{id}` | JWT | Single print job |
| `DELETE` | `/api/prints/{id}` | JWT (super) | Delete a print log |
| `GET`  | `/api/dashboard` | JWT | Dashboard payload (KPIs + charts + recent) |
| `GET`  | `/api/stats` | JWT | KPI numbers only |
| `GET`  | `/api/printers` | JWT | Registered printers |
| `GET`  | `/api/reports` | JWT | Discover available exports |
| `GET`  | `/api/reports/excel` | JWT | Download xlsx |
| `GET`  | `/api/reports/pdf` | JWT | Download PDF |

---

## Deployment to Render

1. Push the repo to GitHub.
2. Create a Postgres database on [Neon](https://neon.tech) and copy the
   pooled connection string.
3. In Render, create a **Blueprint** pointing to `backend/render.yaml`.
4. Configure the secret env vars (`DATABASE_URL`, `JWT_SECRET_KEY`,
   `AGENT_API_KEY`, `DEFAULT_ADMIN_*`, `CORS_ORIGINS`).
5. Deploy. The service auto-creates tables on first boot.

The Dockerfile is also production-ready if you prefer Docker hosting.
