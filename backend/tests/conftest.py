import os
from typing import AsyncGenerator
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Override settings before any import
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-at-least-32-chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CLICKHOUSE_HOST", "localhost")
os.environ.setdefault("CLICKHOUSE_PORT", "8123")
os.environ.setdefault("CLICKHOUSE_USER", "default")
os.environ.setdefault("CLICKHOUSE_PASSWORD", "")
os.environ.setdefault("CLICKHOUSE_DB", "default")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from app.core.database import Base, get_db
from app.main import app

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        # Ensure a clean schema for every pytest session.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client) -> dict:
    """Register a test org+user and return auth headers."""
    suffix = uuid4().hex[:8]
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Test Org",
        "org_slug": f"test-org-{suffix}",
        "email": f"test-{suffix}@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
    })
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def org_a(client) -> dict:
    """Register org A and return {headers, org_id, user_id}."""
    suffix = uuid4().hex[:8]
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Org Alpha",
        "org_slug": f"org-alpha-{suffix}",
        "email": f"admin-{suffix}@org-alpha.com",
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
    suffix = uuid4().hex[:8]
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Org Beta",
        "org_slug": f"org-beta-{suffix}",
        "email": f"admin-{suffix}@org-beta.com",
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
    from sqlalchemy import update

    from app.domains.auth.models import User, UserRole

    suffix = uuid4().hex[:8]
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Platform Org",
        "org_slug": f"platform-org-{suffix}",
        "email": f"superadmin-{suffix}@platform.com",
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
    await db.commit()

    # Re-login to get a fresh token reflecting the new role isn't needed for
    # authorization — role is read from the DB on each request, not from JWT.
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}
