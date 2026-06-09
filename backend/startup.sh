#!/bin/bash
set -e

# Simple Azure App Service startup for CauSium backend
# Oryx handles dependency installation; this just starts gunicorn

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Setup PYTHONPATH for Oryx-installed packages
if [ -d "antenv/lib/python3.12/site-packages" ]; then
    export PYTHONPATH="$(pwd)/antenv/lib/python3.12/site-packages:$(pwd)"
fi

echo "[startup] Python: $(python3 --version 2>&1)"
echo "[startup] Working directory: $(pwd)"
echo "[startup] Starting gunicorn..."

exec python3 -m gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -