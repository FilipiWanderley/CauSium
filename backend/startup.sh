#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Uses system Python and loads dependencies from antenv site-packages via PYTHONPATH.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Resolve system Python (never use antenv/bin/python — glibc mismatch) ---
PY="python3"
if ! command -v python3 &>/dev/null; then
    for p in /opt/python/3.12*/bin/python3 /opt/python/3.*/bin/python3; do
        if [ -x "$p" ]; then PY="$p"; break; fi
    done
fi

echo "[startup] Python: $($PY --version 2>&1)"

# --- Set PYTHONPATH to antenv site-packages (pre-built deps) ---
SITE_PACKAGES="$SCRIPT_DIR/antenv/lib/python3.12/site-packages"
if [ -d "$SITE_PACKAGES" ]; then
    export PYTHONPATH="${SITE_PACKAGES}:${SCRIPT_DIR}:${PYTHONPATH:-}"
    echo "[startup] PYTHONPATH includes antenv site-packages"
else
    export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"
    echo "[startup] WARNING: antenv site-packages not found at $SITE_PACKAGES"
fi

# --- Database ---
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////home/causium-data/causium.db}"
export DATABASE_URL
mkdir -p /home/causium-data

if echo "$DATABASE_URL" | grep -q "^sqlite"; then
    echo "[startup] SQLite mode — skipping alembic."
    WORKERS=1
else
    echo "[startup] PostgreSQL mode — running alembic upgrade head..."
    $PY -m alembic upgrade head
    WORKERS="${GUNICORN_WORKERS:-2}"
fi

# --- Start server ---
PORT="${PORT:-8000}"
echo "[startup] Starting gunicorn (workers=$WORKERS, port=$PORT)..."
exec $PY -m gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT}" \
    --workers "$WORKERS" \
    --timeout 600 \
    --access-logfile - \
    --error-logfile -
