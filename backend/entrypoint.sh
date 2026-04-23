#!/bin/sh
# entrypoint.sh â€” runs Alembic migrations then starts the application.
# Used by both the backend and worker services in docker-compose.
set -e

# Ensure alembic_version uses varchar(128) to accommodate long revision IDs.
# This is idempotent â€” CREATE TABLE IF NOT EXISTS + ALTER column if needed.
echo "[entrypoint] ensuring alembic_version schema..."
python - <<'PYEOF'
import asyncio, os, re
import asyncpg

url = os.environ["DATABASE_URL"]
# Strip the SQLAlchemy dialect prefix: postgresql+asyncpg://... -> asyncpg DSN
m = re.match(r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:/]+):?(\d*)/(.+)", url)
user, password, host, port, database = m.groups()

async def main():
    conn = await asyncpg.connect(
        user=user, password=password,
        host=host, port=int(port or 5432), database=database,
    )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(128) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
    """)
    await conn.execute("""
        ALTER TABLE alembic_version
            ALTER COLUMN version_num TYPE VARCHAR(128)
    """)
    await conn.close()

asyncio.run(main())
PYEOF

echo "[entrypoint] running alembic upgrade head..."
alembic upgrade head
echo "[entrypoint] migrations applied."

exec "$@"
