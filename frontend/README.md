# Print Tracking — Admin Dashboard (React + Vite)

Enterprise dashboard for the **Print Tracking & Monitoring System**.

## Quickstart

```powershell
cd frontend
copy .env.example .env

# Update VITE_API_BASE_URL in .env (defaults to http://localhost:8000/api)

npm install
npm run dev
```

Open <http://localhost:5173> and sign in with the bootstrap admin
credentials configured in the backend (`admin` / `Admin@123` by default —
**change immediately**).

## Build for production

```powershell
npm run build
```

The static bundle is emitted to `dist/`.

## Deployment to Vercel

1. Push the repo to GitHub.
2. In Vercel → New Project → import the repository.
3. Set **Root Directory** to `frontend`.
4. Vite framework is auto-detected; build command and output dir are
   already correct via [`vercel.json`](./vercel.json).
5. Add the environment variable `VITE_API_BASE_URL` pointing to your
   Render backend (e.g. `https://print-tracking-backend.onrender.com/api`).
6. Deploy.

After the first successful deploy, also add the Vercel domain to the
backend `CORS_ORIGINS` env var.

## Pages

| Path | Description |
|---|---|
| `/login` | Admin sign-in |
| `/dashboard` | KPIs, charts, live recent prints (auto-refreshes every 15 s) |
| `/print-logs` | Searchable, filterable, paginated print log table + exports |
| `/analytics` | Trends, top users, top printers, status mix |
| `/reports` | Generate PDF / Excel reports for any date range |
| `/settings` | Account info, registered printers, backend overview |

## Key features

* JWT-based authentication, persisted in `localStorage`
* Real-time auto-refresh on Dashboard and Print Logs
* Server-side pagination, filtering and search
* PDF + Excel export with current filters
* Beautiful dark, fully-responsive enterprise UI
