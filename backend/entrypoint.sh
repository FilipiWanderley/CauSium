#!/bin/sh
# entrypoint.sh — runs Alembic migrations then starts the application.
# Used by both the backend and worker services in docker-compose.
set -e

echo "[entrypoint] running alembic upgrade head..."
alembic upgrade head
echo "[entrypoint] migrations applied."

exec "$@"
