#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   STAGING_API_URL="https://api-staging.example.com" \
#   STAGING_BEARER_TOKEN="<token>" \
#   ./scripts/run_release_rehearsal.sh
#
# Optional:
#   REHEARSAL_REQUESTS=120 REHEARSAL_WARMUP=15 REHEARSAL_MAX_P95_MS=500 \
#   REHEARSAL_OUTPUT_JSON="backend/benchmark_artifacts/release_rehearsal.real.json" \
#   ./scripts/run_release_rehearsal.sh

STAGING_API_URL="${STAGING_API_URL:-}"
STAGING_BEARER_TOKEN="${STAGING_BEARER_TOKEN:-}"
REHEARSAL_REQUESTS="${REHEARSAL_REQUESTS:-120}"
REHEARSAL_WARMUP="${REHEARSAL_WARMUP:-15}"
REHEARSAL_MAX_P95_MS="${REHEARSAL_MAX_P95_MS:-500}"
REHEARSAL_OUTPUT_JSON="${REHEARSAL_OUTPUT_JSON:-backend/benchmark_artifacts/release_rehearsal.real.json}"

if [[ -z "$STAGING_API_URL" ]]; then
  echo "ERROR: STAGING_API_URL is required" >&2
  exit 2
fi

if [[ -z "$STAGING_BEARER_TOKEN" ]]; then
  echo "ERROR: STAGING_BEARER_TOKEN is required" >&2
  exit 2
fi

python3 backend/scripts/release_rehearsal.py \
  --base-url "$STAGING_API_URL" \
  --token "$STAGING_BEARER_TOKEN" \
  --requests "$REHEARSAL_REQUESTS" \
  --warmup "$REHEARSAL_WARMUP" \
  --max-p95-ms "$REHEARSAL_MAX_P95_MS" \
  --output-json "$REHEARSAL_OUTPUT_JSON"

echo "Release rehearsal finished."
echo "Report: $REHEARSAL_OUTPUT_JSON"
