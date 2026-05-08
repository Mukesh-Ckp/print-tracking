#!/usr/bin/env bash
# Production launcher used by Render / Docker.
# Render automatically provides $PORT.

set -euo pipefail

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"

exec gunicorn app.main:app \
    --workers "$WORKERS" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT}" \
    --access-logfile - \
    --error-logfile - \
    --timeout 60 \
    --graceful-timeout 30 \
    --keep-alive 5
