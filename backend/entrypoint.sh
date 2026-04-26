#!/bin/sh
# Runs Alembic migrations before starting the target process.
# Used by backend/worker containers.
set -e

# Ensure alembic_version uses varchar(128) to accommodate long revision IDs.
# This is idempotent â€” CREATE TABLE IF NOT EXISTS + ALTER column if needed.
echo "[entrypoint] Preparing database migration state..."
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
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(128) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)
    except asyncpg.PostgresError as exc:
        # Avoid startup crash when backend and worker run this block concurrently.
        if getattr(exc, "sqlstate", None) != "23505":
            raise
    await conn.execute("""
        ALTER TABLE alembic_version
            ALTER COLUMN version_num TYPE VARCHAR(128)
    """)
    await conn.close()

asyncio.run(main())
PYEOF

echo "[entrypoint] Running migrations: alembic upgrade head"
alembic upgrade head
echo "[entrypoint] Migrations applied successfully."

echo "[entrypoint] Starting process: $*"
exec "$@"
