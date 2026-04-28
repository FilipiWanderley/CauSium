#!/bin/bash
# Azure App Service startup script for CauSium backend.
# Creates a venv using Azure's native Python and caches it in /home
# (persistent across restarts). Rebuilds only when requirements.txt changes.
set -e
cd /home/site/wwwroot

# --- Resolve Python interpreter ---
# Prefer Oryx-created antenv if present; otherwise build our own.
if [ -x "/antenv/bin/python" ]; then
    PY="/antenv/bin/python"
    echo "[startup] Using Oryx antenv"
else
    VENV="/home/causium-venv"
    HASH=$(md5sum requirements.txt 2>/dev/null | cut -c1-8 || echo "none")

    if [ ! -f "$VENV/.hash" ] || [ "$(cat "$VENV/.hash")" != "$HASH" ]; then
        echo "[startup] Building venv with Azure Python (hash=$HASH)..."
        python3 -m venv "$VENV" --clear
        "$VENV/bin/pip" install -r requirements.txt -q --disable-pip-version-check
        echo "$HASH" > "$VENV/.hash"
        echo "[startup] Venv ready."
    else
        echo "[startup] Venv cache hit (hash=$HASH)."
    fi

    PY="$VENV/bin/python"
fi

echo "[startup] Python: $($PY --version)"

# --- Database ---
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./test.db}"
export DATABASE_URL

if echo "$DATABASE_URL" | grep -q "^sqlite"; then
    # SQLite staging: alembic migrations use PostgreSQL-specific types (JSONB etc.)
    # and would fail. Schema is created entirely by ensure_sqlite_schema() in app lifespan.
    echo "[startup] SQLite mode — skipping alembic (schema handled by app lifespan)."
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
