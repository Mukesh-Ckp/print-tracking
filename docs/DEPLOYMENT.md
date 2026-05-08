# Deployment Guide

End-to-end production deployment of the Print Tracking System using:

* **Neon** for managed PostgreSQL
* **Render** for the FastAPI backend
* **Vercel** for the React dashboard
* **The Main Office PC** to host the Python print-agent (Windows service)

---

## 1. Database — Neon Postgres

1. Sign up at <https://neon.tech>.
2. Create a project (e.g. `print-tracking`).
3. Create a database (`print_tracking`).
4. Copy the **pooled connection string**. It looks like:

   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.us-east-2.aws.neon.tech/print_tracking?sslmode=require
   ```

5. The backend automatically converts `postgres://` URLs to
   `postgresql+psycopg2://` — you can paste it as-is.

---

## 2. Backend — Render

### 2a. Push the repo

Push this repository to GitHub. The included
[`backend/render.yaml`](../backend/render.yaml) blueprint defines a
single web service.

### 2b. Create a Render Blueprint

1. In Render → **New** → **Blueprint**.
2. Connect the GitHub repo.
3. Render reads `backend/render.yaml`, fills in non-secret env vars
   automatically.
4. Set the secret environment variables when prompted:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon connection string from step 1 |
   | `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `AGENT_API_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `DEFAULT_ADMIN_USERNAME` | e.g. `ceo` |
   | `DEFAULT_ADMIN_EMAIL` | your real email |
   | `DEFAULT_ADMIN_PASSWORD` | strong password |
   | `CORS_ORIGINS` | `https://your-vercel-domain.vercel.app` (comma-separated for more) |

5. Deploy. First boot takes ~3 min (pip install + initial DB schema).
6. Open `https://<your-service>.onrender.com/health` — it must return
   `{"status":"ok"}`.

The service exposes:

* `https://<host>.onrender.com/`             — service banner
* `https://<host>.onrender.com/health`       — health probe
* `https://<host>.onrender.com/docs`         — Swagger UI
* `https://<host>.onrender.com/api/...`      — API endpoints

### 2c. Notes on Render free tier

Render's free tier sleeps after 15 min idle. The print-agent buffers
events to SQLite if the backend is unavailable; once the service wakes
up the agent flushes them. For zero latency, upgrade to **Starter**
($7/month — `plan: starter` in `render.yaml`).

---

## 3. Frontend — Vercel

1. In Vercel → **New Project** → import the GitHub repo.
2. **Root Directory** = `frontend`. Framework auto-detected as Vite.
3. Build settings (already provided by `frontend/vercel.json`):
   * Build command: `npm run build`
   * Output dir: `dist`
4. Add environment variable:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-render-host>.onrender.com/api` |

5. Deploy. Vercel publishes to a `*.vercel.app` URL.
6. **Add the Vercel domain to the backend CORS** — go to Render → env
   vars → `CORS_ORIGINS` → set to your Vercel domain (with trailing
   `https://`, no slash) and re-deploy.

The dashboard now loads, login with the admin credentials you set.

> **Tip:** The first load after a Render free-tier cold start can take
> 30–60 s while Render boots. Subsequent loads are instant.

---

## 4. Print agent — Main Office PC

This is the only thing that runs on-premise. It connects to the
Render backend over HTTPS and authenticates with the `AGENT_API_KEY`.

### 4a. Copy the agent to the office PC

Copy the entire `print-agent/` folder to the Main Office PC (the one
sharing the printer). Easiest path: `git clone` the repo and `cd
print-agent`.

### 4b. Configure

```powershell
cd print-agent
copy config.example.yaml config.yaml
notepad config.yaml
```

```yaml
api_base_url: https://your-backend.onrender.com/api
api_key: <paste AGENT_API_KEY from Render env vars>
poll_interval_seconds: 1.5
```

### 4c. Install the Windows service

Open **Command Prompt as Administrator**:

```powershell
cd print-agent
service\install_service.bat
```

It will:

* create a venv,
* install dependencies,
* run `pywin32_postinstall`,
* register `PrintTrackingAgent` as an auto-start Windows service,
* start it.

Verify:

```powershell
sc query PrintTrackingAgent
```

Tail the log:

```powershell
Get-Content -Wait .\print-agent\logs\print_agent.log
```

### 4d. Test end-to-end

From any office laptop, print any document to the shared HP Smart
Tank. Within ~2 seconds, the agent log shows `New print job detected`
and the dashboard's "Recent Prints" updates within 15 s.

---

## 5. Hardening checklist

* [ ] Default admin password rotated.
* [ ] `CORS_ORIGINS` locked to the exact Vercel domain (no `*`).
* [ ] `JWT_SECRET_KEY` and `AGENT_API_KEY` both ≥ 48 random chars.
* [ ] HTTPS enabled (Render + Vercel both provide this by default).
* [ ] Backups enabled on Neon (Neon does PITR on paid tier).
* [ ] Service auto-start verified (`sc qc PrintTrackingAgent`).
* [ ] Office PC unattended-restart tested — agent should be RUNNING
      again after the next reboot.

---

## 6. Updates / re-deploys

| Component | Update | Effect |
|---|---|---|
| Backend  | `git push` to GitHub | Render auto-rebuilds and redeploys (~2 min). |
| Frontend | `git push` to GitHub | Vercel auto-rebuilds and redeploys (~30 s). |
| DB schema | Same — `init_db()` is idempotent for the included models. For breaking changes, introduce Alembic migrations. |
| Agent | Replace files on the office PC, then `sc stop PrintTrackingAgent && sc start PrintTrackingAgent`. |

While any of the above are deploying, the print agent buffers
events locally (SQLite) and replays them as soon as the backend is
back up — no data is lost.

---

## 7. Monitoring & logs

* **Backend**: Render dashboard → Logs (live tail). Each request
  carries an `X-Request-ID` header.
* **Frontend**: browser console + Vercel Logs.
* **Print agent**: `print-agent/logs/print_agent.log` (rotated at 5
  MB, 5 backups).
* **Activity audit trail**: every login attempt and every report
  export is recorded in the `activity_logs` table.
