# API Reference

All endpoints are mounted under `/api`. The interactive Swagger UI
at `/docs` (or `https://<host>/docs` in production) is the source of
truth and lets you try every endpoint live.

Two authentication mechanisms are supported:

| Mechanism | Header | Used by |
|---|---|---|
| **JWT** | `Authorization: Bearer <token>` | React dashboard / admin |
| **API key** | `X-API-Key: <secret>` | On-premise print-agent |

---

## Authentication

### `POST /api/auth/login`

Request:

```json
{
  "username": "admin",
  "password": "Admin@123"
}
```

Response (200):

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 43200,
  "admin": {
    "id": 1,
    "username": "admin",
    "email": "admin@printtracking.local",
    "full_name": "System Administrator",
    "is_active": true,
    "is_superuser": true,
    "last_login_at": "2026-05-07T07:14:46Z",
    "created_at": "2026-05-07T07:14:41Z"
  }
}
```

Errors: `401` invalid credentials, `403` disabled account.

### `GET /api/auth/me`

Returns the authenticated admin (JWT required).

---

## Print job ingestion

### `POST /api/print-log` — agent only

Headers: `X-API-Key: <AGENT_API_KEY>`

Request body (every field is optional except as marked):

```json
{
  "username": "alice",
  "computer_name": "ALICE-PC",
  "laptop_ip": "192.168.1.40",
  "printer_name": "HP Smart Tank 660-670 series",
  "printer_ip": "192.168.1.131",
  "document_name": "quarterly-report.docx",
  "pages": 12,
  "copies": 2,
  "total_pages": 24,
  "size_bytes": 583921,
  "paper_size": "A4",
  "color_mode": "color",
  "duplex": "single",
  "status": "completed",
  "submitted_at": "2026-05-07T07:14:00Z",
  "completed_at": "2026-05-07T07:14:18Z",
  "duration_seconds": 18.0,
  "job_id": "HP Smart Tank 660-670 series:1234"
}
```

`status` accepts: `queued | printing | completed | failed | cancelled | paused | unknown`.

Response (201): full `PrintLogOut`.
Errors: `401` (bad/missing API key), `400`/`422` (invalid payload).

---

## Dashboard / stats

### `GET /api/dashboard`

Returns one combined payload that powers the React dashboard:

```json
{
  "stats": {
    "prints_today": 12,
    "pages_today": 47,
    "prints_this_week": 89,
    "pages_this_week": 312,
    "prints_this_month": 312,
    "pages_this_month": 1109,
    "prints_total": 4521,
    "pages_total": 17320,
    "active_users_today": 7,
    "active_printers": 1,
    "failed_today": 0
  },
  "recent_prints": [...],
  "hourly_today":      [{ "label": "00:00", "timestamp": "...", "prints": 0, "pages": 0 }, ...],
  "daily_last_30_days":[{ "label": "2026-04-08", "timestamp": "...", "prints": 5, "pages": 16 }, ...],
  "top_users":   [{ "username": "alice", "prints": 12, "pages": 47 }],
  "top_printers":[{ "printer_name": "HP Smart Tank 660-670 series", "prints": 12, "pages": 47 }],
  "status_breakdown": { "queued": 0, "printing": 0, "completed": 12, "failed": 0, ... },
  "generated_at": "2026-05-07T07:14:46Z"
}
```

### `GET /api/stats`

Same as `dashboard.stats` only.

### `GET /api/printers`

List of registered printers (JWT).

---

## Print logs

### `GET /api/prints`

Query parameters:

| Param | Type | Notes |
|---|---|---|
| `page` | int | default 1 |
| `page_size` | int | default 25, max 200 |
| `search` | string | matches document, user, computer, printer, IP, job_id |
| `username` | string | exact match |
| `computer_name` | string | exact match |
| `printer_name` | string | exact match |
| `status` | enum | `queued`/`printing`/etc |
| `date_from` | ISO 8601 | inclusive lower bound on `received_at` |
| `date_to` | ISO 8601 | inclusive upper bound |

Response:

```json
{
  "items": [PrintLogOut, ...],
  "total": 4521,
  "page": 1,
  "page_size": 25,
  "total_pages": 181
}
```

### `GET /api/prints/{id}`

Single record.

### `DELETE /api/prints/{id}`

Super-admin only (204 No Content on success).

---

## Reports

### `GET /api/reports`

Discovery endpoint listing available exports.

### `GET /api/reports/excel`

Returns an `.xlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).

### `GET /api/reports/pdf`

Returns a landscape A4 PDF report.

Both endpoints accept the same query parameters as `/api/prints` so
the dashboard can pass through the user's current filters. They
return up to 5,000 rows per export (most-recent first); for larger
exports, narrow the date range with `date_from` / `date_to`.

---

## Health

### `GET /health`

```json
{
  "status": "ok",
  "service": "print-tracking-backend",
  "version": "1.0.0",
  "timestamp": "2026-05-07T07:14:46Z"
}
```

Used by Render's health probe and the print-agent's reachability
check.

---

## Errors

All errors follow the standard FastAPI envelope:

```json
{ "detail": "Human-readable error message" }
```

Common status codes:

| Status | Meaning |
|---|---|
| 200 / 201 | Success |
| 204 | Success, no body (DELETE) |
| 400 / 422 | Bad request / validation error |
| 401 | Missing/invalid auth |
| 403 | Authenticated but not authorised |
| 404 | Resource not found |
| 429 | Rate-limited (Render edge) |
| 500 | Server error |

Every response includes `X-Request-ID` (echoed if the client
provided one) and `X-Process-Time-ms` headers, useful when correlating
logs across services.
