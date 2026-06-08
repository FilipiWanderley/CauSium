#!/bin/bash
# Azure App Service startup script for CauSium backend.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[startup] =========================================="
echo "[startup] CauSium Backend Startup"
echo "[startup] =========================================="
echo "[startup] Current directory: $(pwd)"

# Check if antenv exists
ANTENV_DIR="$SCRIPT_DIR/antenv"
if [ -d "$ANTENV_DIR" ] && [ -f "$ANTENV_DIR/bin/python" ]; then
    PY="$ANTENV_DIR/bin/python"
    SITE_PKGS="$ANTENV_DIR/lib/python3.12/site-packages"
    export PYTHONPATH="${SCRIPT_DIR}:${SITE_PKGS}:${PYTHONPATH:-}"
    echo "[startup] Using Oryx-built venv: $PY"
else
    echo "[startup] WARNING: No Oryx venv found, using system Python"
    PY="python3"
    export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"
fi

echo "[startup] Python: $PY"
$PY --version 2>&1

# Database
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL="sqlite+aiosqlite:////home/causium-data/causium.db"
fi
export DATABASE_URL
mkdir -p /home/causium-data

if echo "$DATABASE_URL" | grep -q "^sqlite"; then
    echo "[startup] SQLite mode"
    WORKERS=1
else
    echo "[startup] PostgreSQL mode - running alembic migrations..."
    echo "[startup] alembic current:"
    $PY -m alembic current 2>&1 || echo "alembic current failed"
    echo "[startup] alembic upgrade head:"
    $PY -m alembic upgrade head 2>&1 || echo "alembic upgrade failed"
    WORKERS="${GUNICORN_WORKERS:-2}"
fi

echo "[startup] Starting gunicorn (workers=$WORKERS)..."
exec $PY -m gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "$WORKERS" \
    --timeout 600 \
    --access-logfile - \
    --error-logfile -