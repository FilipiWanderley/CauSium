#!/usr/bin/env bash
# =============================================================================
# StratoPulse — Full restore + RTO measurement (SP-OP10)
#
# Restores all three datastores from a backup produced by backup.sh:
#   PostgreSQL  → pg_restore --clean (drops/recreates objects, then restores)
#   ClickHouse  → TRUNCATE + bulk INSERT … FORMAT Native per table
#   Redis       → replace dump.rdb + graceful container restart
#
# Wall-clock RTO is measured from the first restore command until all three
# services pass their health checks. A JSON report is appended to the
# backup directory.
#
# Usage:
#   ./scripts/restore.sh <backup-directory>
#
#   e.g.:
#   ./scripts/restore.sh backups/2026-04-07_143022
#   SKIP_REDIS=true ./scripts/restore.sh backups/2026-04-07_143022
#
# Exit codes:
#   0  all datastores restored and healthy
#   1  restore failed or health check timed out
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-directory>" >&2
  exit 1
fi

BACKUP_DIR="$(cd "$1" && pwd)"

# ---------------------------------------------------------------------------
# Resolve project root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
POSTGRES_USER="${POSTGRES_USER:-stratopulse}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
POSTGRES_DB="${POSTGRES_DB:-stratopulse}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"

CLICKHOUSE_USER="${CLICKHOUSE_USER:-stratopulse}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-}"
CLICKHOUSE_DB="${CLICKHOUSE_DB:-stratopulse}"
CLICKHOUSE_SERVICE="${CLICKHOUSE_SERVICE:-clickhouse}"

REDIS_SERVICE="${REDIS_SERVICE:-redis}"

# Optional skip flags (useful for partial restores)
SKIP_POSTGRES="${SKIP_POSTGRES:-false}"
SKIP_CLICKHOUSE="${SKIP_CLICKHOUSE:-false}"
SKIP_REDIS="${SKIP_REDIS:-false}"

# Health check timeout in seconds
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
LOG_FILE="$BACKUP_DIR/restore.log"

_log() {
  local level="$1"; shift
  printf "[%s] [%s] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" | tee -a "$LOG_FILE"
}
info()  { _log INFO  "$@"; }
warn()  { _log WARN  "$@"; }
error() { _log ERROR "$@"; }

_ms() {
  if date +%s%3N 2>/dev/null | grep -qE '^[0-9]{13,}$'; then
    date +%s%3N
  else
    python3 -c "import time; print(int(time.time()*1000))"
  fi
}

_elapsed_s() {
  local start_ms="$1" end_ms="$2"
  echo $(( (end_ms - start_ms) / 1000 ))
}

_dc_exec() {
  docker compose -f "$ROOT/docker-compose.yml" exec -T "$@"
}

# Wait for a service to become healthy, polling at 1-second intervals.
# Prints elapsed wait time and returns 0 on success, 1 on timeout.
_wait_healthy() {
  local svc="$1"
  local timeout="${2:-$HEALTH_TIMEOUT}"
  local waited=0
  info "Waiting for $svc to become healthy (timeout: ${timeout}s)..."
  while true; do
    local health
    health=$(
      docker compose -f "$ROOT/docker-compose.yml" ps --format json 2>/dev/null \
        | python3 -c "
import sys, json
data = sys.stdin.read().strip()
# docker compose ps --format json may emit one JSON object per line (not an array)
for line in data.splitlines():
    try:
        obj = json.loads(line)
        if obj.get('Service') == '$svc':
            print(obj.get('Health',''))
    except Exception:
        pass
" 2>/dev/null || true
    )
    if [[ "$health" == "healthy" ]]; then
      info "$svc is healthy (waited ${waited}s)"
      return 0
    fi
    if (( waited >= timeout )); then
      error "$svc did not become healthy within ${timeout}s (last status: ${health:-unknown})"
      return 1
    fi
    sleep 1
    (( waited++ )) || true
  done
}

# ---------------------------------------------------------------------------
# Validate backup directory
# ---------------------------------------------------------------------------
info "==> Restore from: $BACKUP_DIR"
[[ -d "$BACKUP_DIR/postgres" ]]    || { error "Missing postgres/ in backup dir"; exit 1; }
[[ -d "$BACKUP_DIR/clickhouse" ]]  || { error "Missing clickhouse/ in backup dir"; exit 1; }
[[ -d "$BACKUP_DIR/redis" ]]       || { error "Missing redis/ in backup dir"; exit 1; }

# ---------------------------------------------------------------------------
# Read backup report metadata for RPO calculation
# ---------------------------------------------------------------------------
RPO_WINDOW_S=0
BACKUP_END_UTC="unknown"
if [[ -f "$BACKUP_DIR/backup_report.json" ]]; then
  BACKUP_END_UTC=$(python3 -c "
import json, datetime, sys
data = json.load(open('$BACKUP_DIR/backup_report.json'))
print(data.get('backup_end_utc', 'unknown'))
" 2>/dev/null || echo "unknown")

  if [[ "$BACKUP_END_UTC" != "unknown" ]]; then
    RPO_WINDOW_S=$(python3 -c "
import datetime, sys
try:
    t_backup = datetime.datetime.fromisoformat('$BACKUP_END_UTC'.replace('Z','+00:00'))
    t_now    = datetime.datetime.now(datetime.timezone.utc)
    print(int((t_now - t_backup).total_seconds()))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
    info "RPO window: ${RPO_WINDOW_S}s since backup was taken (backup ended: $BACKUP_END_UTC)"
  fi
fi

# ---------------------------------------------------------------------------
# Begin restore — record wall-clock start
# ---------------------------------------------------------------------------
RESTORE_START_MS="$(_ms)"
RESTORE_START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

warn "*** RESTORE IN PROGRESS — DO NOT INTERRUPT ***"

# ---------------------------------------------------------------------------
# 1. PostgreSQL restore
# ---------------------------------------------------------------------------
restore_postgres() {
  info "==> PostgreSQL restore starting"
  local t0; t0="$(_ms)"

  local dump_file="$BACKUP_DIR/postgres/${POSTGRES_DB}.dump"
  [[ -f "$dump_file" ]] || { error "Dump file not found: $dump_file"; return 1; }

  # Drop and recreate the database (--clean alone may leave schemas on older PG)
  _dc_exec \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    "$POSTGRES_SERVICE" \
    psql --username="$POSTGRES_USER" --dbname=postgres \
      --command="DROP DATABASE IF EXISTS \"${POSTGRES_DB}\"" \
    2>&1 | tee -a "$LOG_FILE"

  _dc_exec \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    "$POSTGRES_SERVICE" \
    psql --username="$POSTGRES_USER" --dbname=postgres \
      --command="CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\"" \
    2>&1 | tee -a "$LOG_FILE"

  # Restore using pg_restore
  _dc_exec \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    "$POSTGRES_SERVICE" \
    pg_restore \
      --username="$POSTGRES_USER" \
      --dbname="$POSTGRES_DB" \
      --no-password \
      --single-transaction \
      --exit-on-error \
      - < "$dump_file" \
    2>&1 | tee -a "$LOG_FILE"

  local elapsed; elapsed="$(_elapsed_s "$t0" "$(_ms)")"
  info "PostgreSQL restore complete in ${elapsed}s"
  echo "$elapsed"
}

# ---------------------------------------------------------------------------
# 2. ClickHouse restore
# ---------------------------------------------------------------------------
restore_clickhouse() {
  info "==> ClickHouse restore starting"
  local t0; t0="$(_ms)"

  local table_count=0
  for bin_file in "$BACKUP_DIR/clickhouse/"*.bin; do
    [[ -e "$bin_file" ]] || continue
    local table; table="$(basename "$bin_file" .bin)"
    info "  Restoring ClickHouse table: $table"

    # Truncate first to ensure idempotency
    _dc_exec "$CLICKHOUSE_SERVICE" \
      clickhouse-client \
        --user="$CLICKHOUSE_USER" \
        --password="$CLICKHOUSE_PASSWORD" \
        --query="TRUNCATE TABLE IF EXISTS \`${CLICKHOUSE_DB}\`.\`${table}\`" \
    2>&1 | tee -a "$LOG_FILE"

    # Stream Native binary back in
    _dc_exec "$CLICKHOUSE_SERVICE" \
      clickhouse-client \
        --user="$CLICKHOUSE_USER" \
        --password="$CLICKHOUSE_PASSWORD" \
        --query="INSERT INTO \`${CLICKHOUSE_DB}\`.\`${table}\` FORMAT Native" \
    < "$bin_file" 2>&1 | tee -a "$LOG_FILE"

    (( table_count++ )) || true
  done

  local elapsed; elapsed="$(_elapsed_s "$t0" "$(_ms)")"
  info "ClickHouse restore complete — $table_count table(s) in ${elapsed}s"
  echo "$elapsed"
}

# ---------------------------------------------------------------------------
# 3. Redis restore
# ---------------------------------------------------------------------------
restore_redis() {
  info "==> Redis restore starting"
  local t0; t0="$(_ms)"

  local rdb_file="$BACKUP_DIR/redis/dump.rdb"
  [[ -f "$rdb_file" ]] || { error "RDB file not found: $rdb_file"; return 1; }

  # Copy RDB into the container
  docker compose -f "$ROOT/docker-compose.yml" \
    cp "$rdb_file" "${REDIS_SERVICE}:/data/dump.rdb"

  # Restart Redis so it loads the new RDB on startup
  docker compose -f "$ROOT/docker-compose.yml" restart "$REDIS_SERVICE" \
    2>&1 | tee -a "$LOG_FILE"

  local elapsed; elapsed="$(_elapsed_s "$t0" "$(_ms)")"
  info "Redis restore complete in ${elapsed}s"
  echo "$elapsed"
}

# ---------------------------------------------------------------------------
# Execute restores
# ---------------------------------------------------------------------------
PG_ELAPSED=0
CH_ELAPSED=0
RD_ELAPSED=0
FAILED=false

PG_VERIFY_OK=false
CH_VERIFY_OK=false
RD_VERIFY_OK=false

if [[ "$SKIP_POSTGRES" != "true" ]]; then
  PG_ELAPSED="$(restore_postgres)" || { error "PostgreSQL restore FAILED"; FAILED=true; }
fi

if [[ "$SKIP_CLICKHOUSE" != "true" ]]; then
  CH_ELAPSED="$(restore_clickhouse)" || { error "ClickHouse restore FAILED"; FAILED=true; }
fi

if [[ "$SKIP_REDIS" != "true" ]]; then
  RD_ELAPSED="$(restore_redis)" || { error "Redis restore FAILED"; FAILED=true; }
fi

# ---------------------------------------------------------------------------
# Health verification
# ---------------------------------------------------------------------------
info "==> Verifying datastore health after restore"

if [[ "$SKIP_POSTGRES" != "true" ]]; then
  if _wait_healthy "$POSTGRES_SERVICE" "$HEALTH_TIMEOUT"; then
    # Functional check: run a simple query
    if _dc_exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_SERVICE" \
        psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
          --command="SELECT COUNT(*) FROM information_schema.tables" \
        > /dev/null 2>&1; then
      PG_VERIFY_OK=true
      info "PostgreSQL: VERIFIED OK"
    else
      warn "PostgreSQL: container healthy but query check failed"
    fi
  else
    FAILED=true
  fi
fi

if [[ "$SKIP_CLICKHOUSE" != "true" ]]; then
  if _wait_healthy "$CLICKHOUSE_SERVICE" "$HEALTH_TIMEOUT"; then
    if _dc_exec "$CLICKHOUSE_SERVICE" \
        clickhouse-client \
          --user="$CLICKHOUSE_USER" \
          --password="$CLICKHOUSE_PASSWORD" \
          --query="SELECT 1" \
        > /dev/null 2>&1; then
      CH_VERIFY_OK=true
      info "ClickHouse: VERIFIED OK"
    else
      warn "ClickHouse: container healthy but query check failed"
    fi
  else
    FAILED=true
  fi
fi

if [[ "$SKIP_REDIS" != "true" ]]; then
  if _wait_healthy "$REDIS_SERVICE" "$HEALTH_TIMEOUT"; then
    if _dc_exec "$REDIS_SERVICE" redis-cli PING 2>/dev/null | grep -q PONG; then
      RD_VERIFY_OK=true
      info "Redis: VERIFIED OK"
    else
      warn "Redis: container healthy but PING check failed"
    fi
  else
    FAILED=true
  fi
fi

# ---------------------------------------------------------------------------
# RTO measurement — stop the clock when all healthy
# ---------------------------------------------------------------------------
RESTORE_END_MS="$(_ms)"
RESTORE_END_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RTO_S="$(_elapsed_s "$RESTORE_START_MS" "$RESTORE_END_MS")"
ALL_HEALTHY=$( $FAILED && echo "false" || echo "true" )

# ---------------------------------------------------------------------------
# Write JSON report
# ---------------------------------------------------------------------------
REPORT_FILE="$BACKUP_DIR/restore_report.json"
cat > "$REPORT_FILE" <<EOF
{
  "backup_dir": "$BACKUP_DIR",
  "backup_end_utc": "$BACKUP_END_UTC",
  "rpo_window_seconds": $RPO_WINDOW_S,
  "restore_start_utc": "$RESTORE_START_UTC",
  "restore_end_utc": "$RESTORE_END_UTC",
  "rto_seconds": $RTO_S,
  "restore_durations": {
    "postgres_seconds": $PG_ELAPSED,
    "clickhouse_seconds": $CH_ELAPSED,
    "redis_seconds": $RD_ELAPSED
  },
  "health_checks": {
    "postgres_ok": $PG_VERIFY_OK,
    "clickhouse_ok": $CH_VERIFY_OK,
    "redis_ok": $RD_VERIFY_OK
  },
  "all_healthy": $ALL_HEALTHY
}
EOF

info "==> Restore report: $REPORT_FILE"
cat "$REPORT_FILE" | tee -a "$LOG_FILE"

info "==> RTO: ${RTO_S}s | RPO window: ${RPO_WINDOW_S}s"

if $FAILED; then
  error "Restore completed with errors — see $LOG_FILE"
  exit 1
fi

info "==> Restore SUCCESSFUL"
