#!/usr/bin/env bash
set -euo pipefail

echo "[startup-worker] starting dedicated ingestion worker"
echo "[startup-worker] command: python -m app.workers.ingestion_runner"
echo "[startup-worker] note: no gunicorn/uvicorn, no API startup, no migrations"

export INGESTION_PROCESS=true
exec python -m app.workers.ingestion_runner
