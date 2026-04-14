#!/bin/bash
# CauSium - bootstrap completo para ambiente Docker local
# Faz: build/up -> reset schema -> alembic upgrade head -> smoke auth/economics

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Subindo servicos Docker (backend, worker, frontend)"
docker compose up -d --build backend worker frontend

echo "==> Resetando schema do Postgres (ambiente local)"
docker compose exec -T postgres psql -U causium -d causium -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "==> Aplicando migrations Alembic"
docker compose exec -T backend alembic upgrade head

echo "==> Smoke test: health"
curl -fsS http://localhost:8000/health >/tmp/sp_smoke_health.json

echo "==> Smoke test: register/login/budget"
SUFFIX="$(date +%s)"
EMAIL="smoke-${SUFFIX}@example.com"
SLUG="smoke-org-${SUFFIX}"

curl -fsS -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"org_name\":\"Smoke Org ${SUFFIX}\",\"org_slug\":\"${SLUG}\",\"email\":\"${EMAIL}\",\"full_name\":\"Smoke User\",\"password\":\"smokepassword123\"}" \
  >/tmp/sp_smoke_register.json

curl -fsS -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"smokepassword123\"}" \
  >/tmp/sp_smoke_login.json

TOKEN="$(python3 -c 'import json; print(json.load(open("/tmp/sp_smoke_login.json"))["access_token"])')"

curl -fsS -X PUT http://localhost:8000/api/v1/economics/budget \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"amount_usd":10000,"period":"monthly","currency":"USD","alert_thresholds":[50,80,90]}' \
  >/tmp/sp_smoke_budget.json

echo ""
echo "Bootstrap Docker concluido com sucesso."
echo "- Backend health: /tmp/sp_smoke_health.json"
echo "- Register resp: /tmp/sp_smoke_register.json"
echo "- Login resp: /tmp/sp_smoke_login.json"
echo "- Budget resp: /tmp/sp_smoke_budget.json"
