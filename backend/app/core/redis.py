from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class DisabledRedis:
    """No-op Redis client used when REDIS_URL is not configured."""

    async def ping(self) -> bool:
        return True

    async def get(self, *args: Any, **kwargs: Any) -> Any:
        return None

    async def set(self, *args: Any, **kwargs: Any) -> bool:
        return False

    async def delete(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def incr(self, *args: Any, **kwargs: Any) -> int:
        return 1

    async def eval(self, *args: Any, **kwargs: Any) -> list:
        return [0, 0, 0]

    async def lpush(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def brpop(self, *args: Any, **kwargs: Any) -> Any:
        timeout = kwargs.get("timeout", 0)
        if len(args) >= 2 and isinstance(args[1], int):
            timeout = args[1]
        if timeout and timeout > 0:
            await asyncio.sleep(min(timeout, 1))
        return None

    async def aclose(self) -> None:
        return None


_redis_pool: aioredis.Redis | DisabledRedis | None = None
_redis_pool_loop_id: int | None = None


def get_redis_pool() -> aioredis.Redis | DisabledRedis:
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
        redis_url = settings.redis_url_effective
        if not redis_url:
            log.warning("redis.disabled_no_url")
            _redis_pool = DisabledRedis()
            _redis_pool_loop_id = current_loop_id
            return _redis_pool

        kwargs: dict = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        if redis_url.startswith("rediss://"):
            from app.core.tls import build_ssl_context

            kwargs["ssl"] = build_ssl_context(
                verify=settings.redis_ssl_verify,
                ca_file=settings.redis_ssl_ca_file or None,
                min_version=settings.redis_ssl_min_version,
            )
        _redis_pool = aioredis.from_url(redis_url, **kwargs)
        _redis_pool_loop_id = current_loop_id
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis | DisabledRedis, None]:
    yield get_redis_pool()


async def close_redis() -> None:
    global _redis_pool, _redis_pool_loop_id
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        _redis_pool_loop_id = None
