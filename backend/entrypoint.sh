#!/bin/sh
# Runs Alembic migrations before starting the target process.
# Used by backend/worker containers.
set -e

# Ensure alembic_version uses varchar(128) to accommodate long revision IDs.
# This is idempotent â€” CREATE TABLE IF NOT EXISTS + ALTER column if needed.
echo "[entrypoint] Preparing database migration state..."
python - <<'PYEOF'
import asyncio
import os
import ssl
from urllib.parse import parse_qs, unquote, urlparse

import asyncpg


def _build_connect_kwargs(database_url: str) -> dict:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgresql+asyncpg"}:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("DATABASE_URL is missing hostname")
    if not parsed.path or parsed.path == "/":
        raise ValueError("DATABASE_URL is missing database name")

    query = parse_qs(parsed.query, keep_blank_values=True)
    sslmode = (query.get("sslmode", [None])[0] or "").strip().lower()

    ssl_arg = None
    if sslmode in {"require", "verify-ca", "verify-full"}:
        # Azure Postgres typically requires TLS; use verified context when requested.
        ssl_arg = ssl.create_default_context()
    elif sslmode in {"disable", "allow", "prefer", ""}:
        # Local/dev default: no forced SSL for compatibility.
        ssl_arg = None
    else:
        raise ValueError(f"Unsupported sslmode in DATABASE_URL: {sslmode}")

    return {
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": unquote(parsed.path.lstrip("/")),
        "ssl": ssl_arg,
    }


url = os.environ["DATABASE_URL"]
connect_kwargs = _build_connect_kwargs(url)

async def main():
    conn = await asyncpg.connect(**connect_kwargs)
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
