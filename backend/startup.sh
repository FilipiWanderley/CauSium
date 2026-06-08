#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Uses system Python and installs dependencies from requirements.txt.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Log environment for debugging ---
echo "[startup] Environment:"
echo "  APP_ENV=${APP_ENV}"
echo "  DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'YES' || echo 'NO')"
echo "  REDIS_URL set: $([ -n "$REDIS_URL" ] && echo 'YES' || echo 'NO')"
echo "  CLICKHOUSE_HOST=${CLICKHOUSE_HOST}"
echo "  ENCRYPTION_KEY set: $([ -n "$ENCRYPTION_KEY" ] && echo 'YES' || echo 'NO')"
echo "  SECRET_KEY length: ${#SECRET_KEY}"

# --- Resolve system Python ---
PY="python3"
if ! command -v python3 &>/dev/null; then
    for p in /opt/python/3.12*/bin/python3 /opt/python/3.*/bin/python3; do
        if [ -x "$p" ]; then PY="$p"; break; fi
    done
fi

echo "[startup] Python: $($PY --version 2>&1)"

# --- Install dependencies if not already installed ---
SITE_PACKAGES="$SCRIPT_DIR/antenv/lib/python3.12/site-packages"
if [ -d "$SITE_PACKAGES" ] && [ -f "$SITE_PACKAGES/fastapi/__init__.py" ]; then
    export PYTHONPATH="${SITE_PACKAGES}:${SCRIPT_DIR}:${PYTHONPATH:-}"
    echo "[startup] Using pre-built antenv dependencies"
else
    echo "[startup] Installing dependencies from requirements.txt..."
    $PY -m pip install --quiet --upgrade pip
    $PY -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt" 2>&1 || {
        echo "[startup] Pip install failed, trying with more output..."
        $PY -m pip install -r "$SCRIPT_DIR/requirements.txt"
    }
    echo "[startup] Dependencies installed"
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
    $PY -m alembic upgrade head 2>&1 || echo "[startup] Alembic failed, continuing..."
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
