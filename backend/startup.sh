#!/bin/bash
# Azure App Service startup script for CauSium backend.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[startup] =========================================="
echo "[startup] CauSium Backend Startup"
echo "[startup] =========================================="
echo "[startup] Current directory: $(pwd)"
echo "[startup] APP_ENV=${APP_ENV}"
echo "[startup] DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'YES' || echo 'NO')"

# Use Python from PYTHONPATH or system
if [ -n "$PYTHONPATH" ]; then
    PY_DIR="${PYTHONPATH%%/antenv*}"
    if [ -x "$PY_DIR/python" ]; then
        PY="$PY_DIR/python"
    elif [ -x "$PY_DIR/python3" ]; then
        PY="$PY_DIR/python3"
    fi
fi
PY="${PY:-python3}"

echo "[startup] Using Python: $PY"
$PY --version 2>&1

# Set PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

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
    $PY -m alembic current 2>&1

    echo "[startup] alembic heads:"
    $PY -m alembic heads 2>&1

    echo "[startup] alembic upgrade head:"
    $PY -m alembic upgrade head 2>&1

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