#!/bin/bash
# StratoPulse — local dev setup script
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Copying .env.example → .env (if not exists)"
[ -f "$ROOT/.env" ] || cp "$ROOT/.env.example" "$ROOT/.env"

echo "==> Starting infra (postgres, redis, clickhouse)"
docker compose up -d postgres redis clickhouse

echo "==> Waiting for postgres..."
until docker compose exec postgres pg_isready -U stratopulse 2>/dev/null; do sleep 1; done

echo "==> Installing backend dependencies"
cd "$ROOT/backend"
poetry install

echo "==> Running Alembic migrations"
poetry run alembic upgrade head

echo "==> Starting backend (dev mode)"
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "==> Installing frontend dependencies"
cd "$ROOT/frontend"
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "   Backend:    http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
echo "   Frontend:   run 'npm run dev' in ./frontend/"
echo ""
echo "   To run tests: cd backend && poetry run pytest"
echo "   To stop backend: kill $BACKEND_PID"
echo ""
echo "   Next: register via POST /api/v1/auth/register"
echo "         then go to Settings → Add Account → Sync → Generate"
