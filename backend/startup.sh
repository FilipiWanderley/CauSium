#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Dependencies are pre-installed in antenv/lib/ by CI.
# We use the App Service system Python (compatible glibc) with the
# pre-built site-packages via VIRTUAL_ENV activation.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- Resolve Python interpreter ---
# Use the App Service platform Python (installed by Oryx/platform layer).
# The antenv/ shipped from CI contains only lib/site-packages, not bin/python.
if [ -d "/opt/python" ]; then
    # Azure App Service provides Python under /opt/python/<version>/bin/
    PY=$(find /opt/python -maxdepth 2 -name "python3.12" -type f 2>/dev/null | head -1)
    if [ -z "$PY" ]; then
        PY=$(find /opt/python -maxdepth 2 -name "python3" -type f 2>/dev/null | head -1)
    fi
fi

if [ -z "$PY" ] || [ ! -x "$PY" ]; then
    # Fallback: system python3
    PY="python3"
fi

echo "[startup] Python: $($PY --version 2>&1) at $PY"

# --- Activate virtual environment (site-packages only) ---
# The antenv was built in CI; bin/python was removed (glibc mismatch).
# We activate it so pip-installed scripts (gunicorn, alembic) are on PATH.
if [ -d "$SCRIPT_DIR/antenv" ]; then
    export VIRTUAL_ENV="$SCRIPT_DIR/antenv"
    export PATH="$SCRIPT_DIR/antenv/bin:$PATH"
    # Ensure Python finds the site-packages
    SITE_PACKAGES="$SCRIPT_DIR/antenv/lib/python3.12/site-packages"
    if [ -d "$SITE_PACKAGES" ]; then
        export PYTHONPATH="$SITE_PACKAGES:${PYTHONPATH:-}"
    fi
    echo "[startup] Using antenv site-packages at $SITE_PACKAGES"
else
    echo "[startup] antenv not found — installing deps with system python..."
    $PY -m pip install -r requirements.txt -q --disable-pip-version-check
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
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
