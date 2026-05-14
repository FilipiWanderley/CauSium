from __future__ import annotations

import asyncio
import ssl
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

        # Log connection attempt without exposing credentials
        url_scheme = redis_url.split("://")[0] if "://" in redis_url else "unknown"
        url_host = redis_url.split("@")[-1].split("/")[0] if "@" in redis_url else "(no-auth-segment)"
        log.info(
            "redis.connecting",
            scheme=url_scheme,
            host=url_host,
            ssl_verify=settings.redis_ssl_verify,
            tls_min_version=settings.redis_ssl_min_version if redis_url.startswith("rediss://") else "n/a",
        )

        kwargs: dict = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        if redis_url.startswith("rediss://"):
            tls_version_map: dict[str, ssl.TLSVersion] = {
                "TLSv1.2": ssl.TLSVersion.TLSv1_2,
                "TLSv1.3": ssl.TLSVersion.TLSv1_3,
            }
            kwargs["ssl_cert_reqs"] = "required" if settings.redis_ssl_verify else "none"
            kwargs["ssl_check_hostname"] = settings.redis_ssl_verify
            if settings.redis_ssl_ca_file:
                kwargs["ssl_ca_certs"] = settings.redis_ssl_ca_file
            kwargs["ssl_min_version"] = tls_version_map.get(
                settings.redis_ssl_min_version,
                ssl.TLSVersion.TLSv1_3,
            )
        _redis_pool = aioredis.from_url(redis_url, **kwargs)
        _redis_pool_loop_id = current_loop_id
        log.info("redis.pool_created", scheme=url_scheme, host=url_host)
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis | DisabledRedis, None]:
    yield get_redis_pool()


async def close_redis() -> None:
    global _redis_pool, _redis_pool_loop_id
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        _redis_pool_loop_id = None
