import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override settings before any import
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-at-least-32-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CLICKHOUSE_HOST", "localhost")
os.environ.setdefault("CLICKHOUSE_PORT", "8123")
os.environ.setdefault("CLICKHOUSE_USER", "default")
os.environ.setdefault("CLICKHOUSE_PASSWORD", "")
os.environ.setdefault("CLICKHOUSE_DB", "default")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItdGVzdHM=")

from app.core.database import Base, get_db
from app.main import app

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client) -> dict:
    """Register a test org+user and return auth headers."""
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Test Org",
        "org_slug": "test-org",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
    })
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def org_a(client) -> dict:
    """Register org A and return {headers, org_id, user_id}."""
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Org Alpha",
        "org_slug": "org-alpha",
        "email": "admin@org-alpha.com",
        "full_name": "Alpha Admin",
        "password": "alphapassword123",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "org_id": data["user"]["org_id"],
        "user_id": data["user"]["id"],
    }


@pytest_asyncio.fixture
async def org_b(client) -> dict:
    """Register org B and return {headers, org_id, user_id}."""
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Org Beta",
        "org_slug": "org-beta",
        "email": "admin@org-beta.com",
        "full_name": "Beta Admin",
        "password": "betapassword123",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "org_id": data["user"]["org_id"],
        "user_id": data["user"]["id"],
    }


@pytest_asyncio.fixture
async def platform_admin_headers(client, db) -> dict:
    """
    Register org C, then directly elevate its admin to PLATFORM_ADMIN in the DB,
    and return auth headers.
    """
    from sqlalchemy import select, update

    from app.domains.auth.models import User, UserRole

    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Platform Org",
        "org_slug": "platform-org",
        "email": "superadmin@platform.com",
        "full_name": "Platform Superadmin",
        "password": "superpassword123",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    user_id = data["user"]["id"]

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(role=UserRole.PLATFORM_ADMIN)
    )
    await db.flush()

    # Re-login to get a fresh token reflecting the new role isn't needed for
    # authorization — role is read from the DB on each request, not from JWT.
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}
