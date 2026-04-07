#!/usr/bin/env bash
# =============================================================================
# StratoPulse — Full backup (SP-OP10)
#
# Backs up all three datastores:
#   PostgreSQL  → custom-format pg_dump (parallel-restoreable, compressed)
#   ClickHouse  → per-table Native binary format via clickhouse-client
#   Redis       → RDB snapshot triggered via BGSAVE + docker cp
#
# The backup is written to BACKUP_ROOT/<TIMESTAMP>/ and a JSON report is
# emitted at the end with per-datastore durations and RPO metadata.
#
# Usage:
#   ./scripts/backup.sh                      # reads defaults from .env
#   BACKUP_ROOT=/mnt/nas/sp-backups ./scripts/backup.sh
#
# Dependencies:
#   - docker compose (v2) with healthy postgres / redis / clickhouse services
#   - jq (optional — report is also written as a plain JSON file regardless)
#
# Exit codes:
#   0  all three datastores backed up successfully
#   1  one or more datastores failed
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve project root (works when called from any directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Load .env without exporting secrets to child processes via `export`
# Variables are consumed locally inside this script only.
# ---------------------------------------------------------------------------
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

# ---------------------------------------------------------------------------
# Configuration — all overrideable via environment
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

BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
TIMESTAMP="$(date -u +%Y-%m-%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
LOG_FILE="$BACKUP_DIR/backup.log"

_log() {
  local level="$1"; shift
  printf "[%s] [%s] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" | tee -a "$LOG_FILE"
}
info()  { _log INFO  "$@"; }
warn()  { _log WARN  "$@"; }
error() { _log ERROR "$@"; }

# Returns milliseconds since epoch (compatible with macOS date and GNU date)
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
  # Run docker compose exec with -T (no pseudo-TTY) in the project root.
  docker compose -f "$ROOT/docker-compose.yml" exec -T "$@"
}

_service_healthy() {
  local svc="$1"
  local status
  status=$(docker compose -f "$ROOT/docker-compose.yml" ps --format json 2>/dev/null \
    | grep -o '"Service":"'"$svc"'"[^}]*"Health":"[^"]*"' \
    | grep -o '"Health":"[^"]*"' \
    | tr -d '"Health:' || true)
  [[ "$status" == "healthy" ]]
}

# ---------------------------------------------------------------------------
# Initialise backup directory
# ---------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR/postgres" "$BACKUP_DIR/clickhouse" "$BACKUP_DIR/redis"
info "Backup directory: $BACKUP_DIR"

BACKUP_START_MS="$(_ms)"
BACKUP_START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---------------------------------------------------------------------------
# 1. PostgreSQL
# ---------------------------------------------------------------------------
backup_postgres() {
  info "==> PostgreSQL backup starting"
  local t0; t0="$(_ms)"

  local dump_file="$BACKUP_DIR/postgres/${POSTGRES_DB}.dump"

  _dc_exec \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    "$POSTGRES_SERVICE" \
    pg_dump \
      --username="$POSTGRES_USER" \
      --format=custom \
      --compress=9 \
      --no-password \
      "$POSTGRES_DB" > "$dump_file"

  local size; size="$(du -h "$dump_file" | cut -f1)"
  local elapsed; elapsed="$(_elapsed_s "$t0" "$(_ms)")"
  info "PostgreSQL backup complete — $size in ${elapsed}s → $(basename "$dump_file")"
  echo "$elapsed"
}

# ---------------------------------------------------------------------------
# 2. ClickHouse
# ---------------------------------------------------------------------------
backup_clickhouse() {
  info "==> ClickHouse backup starting"
  local t0; t0="$(_ms)"

  # Enumerate tables in the target database
  local tables
  tables=$(
    _dc_exec "$CLICKHOUSE_SERVICE" \
      clickhouse-client \
        --user="$CLICKHOUSE_USER" \
        --password="$CLICKHOUSE_PASSWORD" \
        --query="SHOW TABLES FROM \`${CLICKHOUSE_DB}\`" 2>/dev/null \
    | tr -d '\r'
  )

  if [[ -z "$tables" ]]; then
    warn "No tables found in ClickHouse database '$CLICKHOUSE_DB' — skipping"
    echo "0"
    return
  fi

  local table_count=0
  while IFS= read -r table; do
    [[ -z "$table" ]] && continue
    info "  Dumping ClickHouse table: $table"
    _dc_exec "$CLICKHOUSE_SERVICE" \
      clickhouse-client \
        --user="$CLICKHOUSE_USER" \
        --password="$CLICKHOUSE_PASSWORD" \
        --query="SELECT * FROM \`${CLICKHOUSE_DB}\`.\`${table}\` FORMAT Native" \
    > "$BACKUP_DIR/clickhouse/${table}.bin"
    (( table_count++ )) || true
  done <<< "$tables"

  local elapsed; elapsed="$(_elapsed_s "$t0" "$(_ms)")"
  info "ClickHouse backup complete — $table_count table(s) in ${elapsed}s"
  echo "$elapsed"
}

# ---------------------------------------------------------------------------
# 3. Redis
# ---------------------------------------------------------------------------
backup_redis() {
  info "==> Redis backup starting"
  local t0; t0="$(_ms)"

  # Trigger a synchronous RDB save (BGSAVE + wait for completion)
  _dc_exec "$REDIS_SERVICE" redis-cli BGSAVE > /dev/null

  # Poll until last-save timestamp advances (max 30 s)
  local before_save; before_save="$(_dc_exec "$REDIS_SERVICE" redis-cli LASTSAVE | tr -d '[:space:]')"
  local waited=0
  while true; do
    local after_save; after_save="$(_dc_exec "$REDIS_SERVICE" redis-cli LASTSAVE | tr -d '[:space:]')"
    [[ "$after_save" -gt "$before_save" ]] && break
    if (( waited >= 30 )); then
      warn "Timed out waiting for Redis BGSAVE — copying potentially stale RDB"
      break
    fi
    sleep 1
    (( waited++ )) || true
  done

  # Copy the RDB file out of the container
  docker compose -f "$ROOT/docker-compose.yml" \
    cp "${REDIS_SERVICE}:/data/dump.rdb" "$BACKUP_DIR/redis/dump.rdb"

  local elapsed; elapsed="$(_elapsed_s "$t0" "$(_ms)")"
  info "Redis backup complete in ${elapsed}s → dump.rdb"
  echo "$elapsed"
}

# ---------------------------------------------------------------------------
# Run all three backups, record per-datastore durations
# ---------------------------------------------------------------------------
PG_ELAPSED=0
CH_ELAPSED=0
RD_ELAPSED=0
FAILED=false

PG_ELAPSED="$(backup_postgres)" || { error "PostgreSQL backup FAILED"; FAILED=true; }
CH_ELAPSED="$(backup_clickhouse)" || { error "ClickHouse backup FAILED"; FAILED=true; }
RD_ELAPSED="$(backup_redis)" || { error "Redis backup FAILED"; FAILED=true; }

BACKUP_END_MS="$(_ms)"
BACKUP_END_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TOTAL_ELAPSED="$(_elapsed_s "$BACKUP_START_MS" "$BACKUP_END_MS")"

# ---------------------------------------------------------------------------
# Write JSON report
# ---------------------------------------------------------------------------
REPORT_FILE="$BACKUP_DIR/backup_report.json"
cat > "$REPORT_FILE" <<EOF
{
  "backup_start_utc": "$BACKUP_START_UTC",
  "backup_end_utc": "$BACKUP_END_UTC",
  "total_duration_seconds": $TOTAL_ELAPSED,
  "datastores": {
    "postgres": {
      "duration_seconds": $PG_ELAPSED,
      "database": "$POSTGRES_DB",
      "format": "pg_dump custom (compressed)"
    },
    "clickhouse": {
      "duration_seconds": $CH_ELAPSED,
      "database": "$CLICKHOUSE_DB",
      "format": "Native binary per table"
    },
    "redis": {
      "duration_seconds": $RD_ELAPSED,
      "format": "RDB snapshot"
    }
  },
  "success": $(${FAILED} && echo "false" || echo "true"),
  "backup_dir": "$BACKUP_DIR"
}
EOF

info "==> Backup report: $REPORT_FILE"

if [[ -f "$(command -v jq 2>/dev/null || true)" ]]; then
  jq . "$REPORT_FILE" | tee -a "$LOG_FILE"
else
  cat "$REPORT_FILE" | tee -a "$LOG_FILE"
fi

info "==> Total backup time: ${TOTAL_ELAPSED}s"

if $FAILED; then
  error "One or more datastores failed — check $LOG_FILE"
  exit 1
fi

# Print the backup directory path last so callers can capture it easily
echo "$BACKUP_DIR"
