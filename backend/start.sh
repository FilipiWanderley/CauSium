#!/usr/bin/env bash
echo "[start] Starting at $(date)"
echo "[start] Current dir: $(pwd)"
echo "[start] Checking antenv..."
if [ -f "/home/site/wwwroot/antenv/bin/python" ]; then
    echo "[start] antenv python found"
    /home/site/wwwroot/antenv/bin/python --version
else
    echo "[start] antenv NOT found!"
    ls -la /home/site/wwwroot/ | head -20
fi
echo "[start] Running gunicorn..."
cd /home/site/wwwroot
export PYTHONPATH=/home/site/wwwroot:/home/site/wwwroot/antenv/lib/python3.12/site-packages
exec /home/site/wwwroot/antenv/bin/python -m gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2 --timeout 600