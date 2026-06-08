#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Uses system Python and installs dependencies from requirements.txt.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Log environment for debugging ---
echo "[startup] =========================================="
echo "[startup] CauSium Backend Startup"
echo "[startup] =========================================="
echo "[startup] Current directory: $(pwd)"
echo "[startup] APP_ENV=${APP_ENV}"
echo "[startup] DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'YES' || echo 'NO')"
echo "[startup] REDIS_URL set: $([ -n "$REDIS_URL" ] && echo 'YES' || echo 'NO')"
echo "[startup] CLICKHOUSE_HOST=${CLICKHOUSE_HOST}"
echo "[startup] ENCRYPTION_KEY set: $([ -n "$ENCRYPTION_KEY" ] && echo 'YES' || echo 'NO')"
echo "[startup] SECRET_KEY length: ${#SECRET_KEY}"

# --- Resolve Python from PYTHONPATH env or system ---
PYTHON_BIN="${PYTHONPATH%%:*}"
if [ -n "$PYTHON_BIN" ] && [ -x "$PYTHON_BIN/python" ]; then
    PY="$PYTHON_BIN/python"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    for p in /opt/python/3.12*/bin/python3 /opt/python/3.*/bin/python3; do
        if [ -x "$p" ]; then PY="$p"; break; fi
    done
fi

PY="${PY:-python3}"
echo "[startup] Using Python: $PY"
$PY --version 2>&1 || echo "[startup] Python not found!"

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
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL="sqlite+aiosqlite:////home/causium-data/causium.db"
fi
export DATABASE_URL
mkdir -p /home/causium-data

if echo "$DATABASE_URL" | grep -q "^sqlite"; then
    echo "[startup] SQLite mode — skipping alembic."
    WORKERS=1
else
    echo "[startup] PostgreSQL mode — running alembic migrations..."

    # Set PYTHONPATH correctly
    export PYTHONPATH="${SCRIPT_DIR}:${SITE_PACKAGES}:${PYTHONPATH:-}"

    # Navigate to backend directory for alembic
    cd "$SCRIPT_DIR"

    # Log alembic status
    echo "[startup] =========================================="
    echo "[startup] Alembic Migration Status"
    echo "[startup] =========================================="
    echo "[startup] Current directory: $(pwd)"
    echo "[startup] PYTHONPATH: ${PYTHONPATH}"
    echo "[startup] DATABASE_URL: ${DATABASE_URL%%@*}@***"  # Hide password

    echo "[startup] Running: python -m alembic current"
    $PY -m alembic current 2>&1 || echo "[startup] alembic current failed: $?"

    echo "[startup] Running: python -m alembic heads"
    $PY -m alembic heads 2>&1 || echo "[startup] alembic heads failed: $?"

    echo "[startup] =========================================="
    echo "[startup] Running: python -m alembic upgrade head"
    echo "[startup] =========================================="

    # Run migrations and capture output
    if $PY -m alembic upgrade head 2>&1; then
        echo "[startup] alembic upgrade head: SUCCESS"
    else
        echo "[startup] WARNING: alembic upgrade head failed - continuing anyway for debugging"
    fi

    echo "[startup] =========================================="
    echo "[startup] Migration complete, starting server..."
    echo "[startup] =========================================="

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