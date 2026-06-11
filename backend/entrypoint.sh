#!/bin/sh
# Production entrypoint - NO migrations (disabled for hotfix)
# Migrations should be run via CI/CD, not at startup

set -e

echo "[entrypoint] Starting application (migrations disabled)"

# Execute the command passed as arguments
exec "$@"
