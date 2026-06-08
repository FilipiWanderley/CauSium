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
if [ ! -d "$ANTENV_DIR" ]; then
    echo "[startup] Creating virtual environment..."
    python3 -m venv "$ANTENV_DIR"
    echo "[startup] Virtual environment created"
fi

# Activate virtual environment
source "$ANTENV_DIR/bin/activate"

# Install dependencies
echo "[startup] Installing dependencies..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"
echo "[startup] Dependencies installed"

# Set PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/antenv/lib/python3.12/site-packages:${PYTHONPATH:-}"

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
    python -m alembic current 2>&1

    echo "[startup] alembic heads:"
    python -m alembic heads 2>&1

    echo "[startup] alembic upgrade head:"
    python -m alembic upgrade head 2>&1

    WORKERS="${GUNICORN_WORKERS:-2}"
fi

echo "[startup] Starting gunicorn (workers=$WORKERS)..."
exec gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "$WORKERS" \
    --timeout 600 \
    --access-logfile - \
    --error-logfile -