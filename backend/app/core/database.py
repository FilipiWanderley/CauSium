import logging
import ssl
from typing import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker as sync_sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    __allow_unmapped__ = True


def create_engine():
    settings = get_settings()
    database_url = settings.database_url_effective

    # SQLite fallback mode (staging): avoid PostgreSQL-specific pool/SSL args.
    if database_url.startswith("sqlite+aiosqlite://"):
        return create_async_engine(
            database_url,
            echo=not settings.is_production,
            pool_pre_ping=True,
        )

    connect_args: dict = {}
    if settings.db_ssl_enabled or settings.is_production:
        ssl_ctx = ssl.create_default_context()
        if settings.db_ssl_ca_file:
            ssl_ctx.load_verify_locations(cafile=settings.db_ssl_ca_file)
        if not settings.db_ssl_verify:
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx
    return create_async_engine(
        database_url,
        echo=not settings.is_production,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
    )


engine = create_engine()

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# Sync engine/session for internal non-critical queries (e.g., settings reads)
_sync_engine = None
_sync_session_factory = None


def get_sync_session_factory():
    """Get or create a sync session factory for internal queries."""
    global _sync_engine, _sync_session_factory
    if _sync_session_factory is None:
        settings = get_settings()
        database_url = settings.database_url_effective
        # Convert async URL to sync URL (strip aiosqlite prefix)
        sync_url = database_url.replace("+aiosqlite", "").replace("sqlite:", "sqlite:")
        _sync_engine = create_async_engine(sync_url, echo=False)
        _sync_session_factory = sync_sessionmaker(_sync_engine, expire_on_commit=False)
    return _sync_session_factory


async def ensure_sqlite_schema() -> None:
    settings = get_settings()
    if not settings.database_url_effective.startswith("sqlite+aiosqlite://"):
        return
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except OperationalError as exc:
        if "already exists" in str(exc):
            logger.warning("ensure_sqlite_schema: tables already exist (race), skipping")
        else:
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
