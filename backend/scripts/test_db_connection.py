from __future__ import annotations

import asyncio
import os
from urllib.parse import urlsplit, urlunsplit

import asyncpg


def _to_asyncpg_dsn(database_url: str) -> str:
    parts = urlsplit(database_url)
    scheme = parts.scheme.lower()
    if scheme == "postgresql+asyncpg":
        return urlunsplit(("postgresql", parts.netloc, parts.path, parts.query, parts.fragment))
    return database_url


async def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    conn = await asyncpg.connect(dsn=_to_asyncpg_dsn(database_url))
    try:
        row = await conn.fetchrow("SELECT current_database() AS db, current_user AS user, version() AS version")
        print("Connection OK")
        print(f"Database: {row['db']}")
        print(f"User: {row['user']}")
        print(f"Server: {str(row['version']).split(',')[0]}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
