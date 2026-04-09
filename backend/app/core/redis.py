from __future__ import annotations
import asyncio
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import get_settings

_redis_pool: aioredis.Redis | None = None
_redis_pool_loop_id: int | None = None


def get_redis_pool() -> aioredis.Redis:
    global _redis_pool, _redis_pool_loop_id

    current_loop_id: int | None = None
    try:
        current_loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        current_loop_id = None

    if _redis_pool is not None and _redis_pool_loop_id is not None and _redis_pool_loop_id != current_loop_id:
        _redis_pool = None
        _redis_pool_loop_id = None

    if _redis_pool is None:
        settings = get_settings()
        kwargs: dict = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        if settings.redis_url.startswith("rediss://"):
            from app.core.tls import build_ssl_context

            kwargs["ssl"] = build_ssl_context(
                verify=settings.redis_ssl_verify,
                ca_file=settings.redis_ssl_ca_file or None,
                min_version=settings.redis_ssl_min_version,
            )
        _redis_pool = aioredis.from_url(settings.redis_url, **kwargs)
        _redis_pool_loop_id = current_loop_id
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield get_redis_pool()


async def close_redis() -> None:
    global _redis_pool, _redis_pool_loop_id
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        _redis_pool_loop_id = None
