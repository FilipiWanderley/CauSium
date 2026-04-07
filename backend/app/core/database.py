from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    __allow_unmapped__ = True


def create_engine():
    settings = get_settings()
    connect_args: dict = {}
    if settings.db_ssl_enabled or settings.is_production:
        from app.core.tls import maybe_ssl_context

        ssl_ctx = maybe_ssl_context(
            enabled=True,
            verify=settings.db_ssl_verify,
            ca_file=settings.db_ssl_ca_file or None,
            min_version=settings.db_ssl_min_version,
        )
        if ssl_ctx:
            connect_args["ssl"] = ssl_ctx
    return create_async_engine(
        settings.database_url,
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
