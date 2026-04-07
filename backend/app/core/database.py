from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    __allow_unmapped__ = True


def create_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=not settings.is_production,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
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
