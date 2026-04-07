#!/usr/bin/env bash
# =============================================================================
# StratoPulse — Automated RTO/RPO drill (SP-OP10)
#
# Orchestrates a full backup → restore cycle in a controlled environment and
# emits a consolidated JSON report with RPO and RTO measurements.  Run this
# periodically in staging to keep the RTO/RPO targets honest.
#
# Targets (adjust via env vars):
#   RTO_TARGET_S  — maximum acceptable restore time in seconds  (default: 300 = 5 min)
#   RPO_TARGET_S  — maximum acceptable data age at restore time (default: 3600 = 1 h)
#
# Usage:
#   ./scripts/rto_rpo_test.sh                # full drill
#   DRY_RUN=true ./scripts/rto_rpo_test.sh   # backup only, no restore
#
# The report is written to BACKUP_ROOT/<TIMESTAMP>/rto_rpo_report.json and
# to stdout. Exit code 0 means all targets met; 1 means any target was missed.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Drill targets
RTO_TARGET_S="${RTO_TARGET_S:-300}"
RPO_TARGET_S="${RPO_TARGET_S:-3600}"
DRY_RUN="${DRY_RUN:-false}"

BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
DRILL_START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_log() {
  printf "[%s] [DRILL] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}
info()  { _log "INFO  $*"; }
warn()  { _log "WARN  $*"; }
error() { _log "ERROR $*"; }

_bool() {
  [[ "$1" == "true" ]] && echo "true" || echo "false"
}

# ---------------------------------------------------------------------------
# Step 1 — Backup
# ---------------------------------------------------------------------------
info "Starting backup..."
backup_output="$("$SCRIPT_DIR/backup.sh" 2>&1)"
backup_exit=$?
echo "$backup_output"

if (( backup_exit != 0 )); then
  error "Backup failed — aborting drill"
  exit 1
fi

# Capture the backup directory from the last line of backup.sh output
BACKUP_DIR="$(echo "$backup_output" | tail -1)"

if [[ ! -d "$BACKUP_DIR" ]]; then
  error "Could not determine backup directory from backup.sh output"
  exit 1
fi

info "Backup directory: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# Step 2 — Restore (unless DRY_RUN)
# ---------------------------------------------------------------------------
RTO_S=0
RPO_WINDOW_S=0
ALL_HEALTHY=false
RTO_MET=false
RPO_MET=false

if [[ "$DRY_RUN" == "true" ]]; then
  warn "DRY_RUN=true — skipping restore step"
  ALL_HEALTHY=true  # unknown, assume ok in dry-run
else
  info "Starting restore from: $BACKUP_DIR"
  restore_output="$("$SCRIPT_DIR/restore.sh" "$BACKUP_DIR" 2>&1)"
  restore_exit=$?
  echo "$restore_output"

  if (( restore_exit != 0 )); then
    error "Restore step failed"
    # NOTE: we still emit the report before exiting
  fi

  # Parse the restore report to extract measurements
  RESTORE_REPORT="$BACKUP_DIR/restore_report.json"
  if [[ -f "$RESTORE_REPORT" ]]; then
    RTO_S="$(python3 -c "import json; d=json.load(open('$RESTORE_REPORT')); print(d['rto_seconds'])")"
    RPO_WINDOW_S="$(python3 -c "import json; d=json.load(open('$RESTORE_REPORT')); print(d['rpo_window_seconds'])")"
    ALL_HEALTHY="$(python3 -c "import json; d=json.load(open('$RESTORE_REPORT')); print(str(d['all_healthy']).lower())")"
  fi
fi

# ---------------------------------------------------------------------------
# Evaluate against targets
# ---------------------------------------------------------------------------
if (( RTO_S <= RTO_TARGET_S )) && [[ "$ALL_HEALTHY" == "true" ]]; then
  RTO_MET=true
fi

if (( RPO_WINDOW_S <= RPO_TARGET_S )); then
  RPO_MET=true
fi

DRILL_PASS=$( [[ "$RTO_MET" == "true" && "$RPO_MET" == "true" ]] && echo "true" || echo "false" )

# ---------------------------------------------------------------------------
# Write consolidated report
# ---------------------------------------------------------------------------
DRILL_END_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
REPORT_FILE="$BACKUP_DIR/rto_rpo_report.json"

cat > "$REPORT_FILE" <<EOF
{
  "drill_start_utc": "$DRILL_START_UTC",
  "drill_end_utc": "$DRILL_END_UTC",
  "backup_dir": "$BACKUP_DIR",
  "dry_run": $(_bool "$DRY_RUN"),
  "measurements": {
    "rto_seconds": $RTO_S,
    "rpo_window_seconds": $RPO_WINDOW_S,
    "all_services_healthy": $(_bool "$ALL_HEALTHY")
  },
  "targets": {
    "rto_target_seconds": $RTO_TARGET_S,
    "rpo_target_seconds": $RPO_TARGET_S
  },
  "results": {
    "rto_met": $(_bool "$RTO_MET"),
    "rpo_met": $(_bool "$RPO_MET"),
    "drill_passed": $(_bool "$DRILL_PASS")
  }
}
EOF

echo ""
echo "============================================================"
echo "  StratoPulse RTO/RPO Drill Report"
echo "============================================================"
printf "  RTO achieved : %4ds  (target ≤ %ds)  %s\n" \
  "$RTO_S" "$RTO_TARGET_S" "$( [[ "$RTO_MET" == "true" ]] && echo "PASS ✓" || echo "FAIL ✗")"
printf "  RPO window   : %4ds  (target ≤ %ds)  %s\n" \
  "$RPO_WINDOW_S" "$RPO_TARGET_S" "$( [[ "$RPO_MET" == "true" ]] && echo "PASS ✓" || echo "FAIL ✗")"
printf "  All healthy  : %-5s\n" "$ALL_HEALTHY"
echo "  Report       : $REPORT_FILE"
echo "============================================================"

if [[ "$DRILL_PASS" == "true" ]]; then
  info "Drill PASSED — all RTO/RPO targets met"
  exit 0
else
  error "Drill FAILED — one or more targets missed"
  exit 1
fi
