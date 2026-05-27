#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Uses the antenv created by Oryx during build — no venv rebuild needed.
set -e

# Oryx extracts the app to a temp dir and sets PYTHONPATH.
# The antenv is at <appdir>/antenv — find it relative to this script.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Resolve Python interpreter ---
# Oryx antenv is always at <appdir>/antenv after build
if [ -x "$SCRIPT_DIR/antenv/bin/python" ]; then
    PY="$SCRIPT_DIR/antenv/bin/python"
    echo "[startup] Using antenv at $SCRIPT_DIR/antenv"
elif [ -x "/antenv/bin/python" ]; then
    PY="/antenv/bin/python"
    echo "[startup] Using /antenv"
else
    # Fallback: use system python and install deps
    echo "[startup] antenv not found — installing deps with system python..."
    python3 -m pip install -r requirements.txt -q --disable-pip-version-check
    PY="python3"
fi

echo "[startup] Python: $($PY --version 2>&1)"

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
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
