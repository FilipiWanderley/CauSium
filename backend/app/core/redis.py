from __future__ import annotations
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import get_settings

_redis_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield get_redis_pool()


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
