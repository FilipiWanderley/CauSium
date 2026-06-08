#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Assumes Oryx builder has already created the virtual environment.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[startup] =========================================="
echo "[startup] CauSium Backend Startup"
echo "[startup] =========================================="
echo "[startup] Current directory: $(pwd)"
echo "[startup] APP_ENV=${APP_ENV}"
echo "[startup] DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'YES' || echo 'NO')"

# Try to use existing venv first, skip pip install if already done
ANTENV_DIR="$SCRIPT_DIR/antenv"
SITE_PKGS="$ANTENV_DIR/lib/python3.12/site-packages"

if [ -d "$SITE_PKGS" ] && [ -f "$SITE_PKGS/fastapi/__init__.py" ]; then
    echo "[startup] Using existing venv from Oryx build"
    export PYTHONPATH="${SCRIPT_DIR}:${SITE_PKGS}:${PYTHONPATH:-}"
    PY="python3"
else
    echo "[startup] WARNING: No pre-built venv found, trying to use system Python"
    export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"
    PY="python3"
fi

echo "[startup] Using Python: $PY"
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

    cd "$SCRIPT_DIR"
    echo "[startup] alembic current:"
    $PY -m alembic current 2>&1 || echo "alembic current failed"

    echo "[startup] alembic heads:"
    $PY -m alembic heads 2>&1 || echo "alembic heads failed"

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