from __future__ import annotations
import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis_pool
from app.core.security import decode_token

log = get_logger(__name__)


def _extract_org_id(request: Request) -> str | None:
    token: str | None = None

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip() or None

    if not token:
        from app.core.config import get_settings

        token = request.cookies.get(get_settings().auth_cookie_access_name)

    if not token:
        return None

    try:
        payload = decode_token(token)
    except Exception:
        return None

    if payload.get("type") != "access":
        return None

    org_id = payload.get("org_id")
    return str(org_id) if org_id else None


def _apply_security_headers(response: Response) -> None:
    settings = get_settings()
    if not settings.security_headers_enabled:
        return

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = settings.csp_policy
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


def install_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable):
        settings = get_settings()

        path = request.url.path
        if not settings.rate_limit_enabled or not path.startswith("/api/"):
            response = await call_next(request)
            _apply_security_headers(response)
            return response

        ip = request.client.host if request.client else "unknown"
        org_id = _extract_org_id(request)
        minute_bucket = int(time.time() // 60)

        key_limits: list[tuple[str, int]] = []
        if path.startswith("/api/v1/auth"):
            key_limits.append((f"rl:ip:auth:{ip}:{minute_bucket}", settings.rate_limit_auth_ip_per_minute))
        else:
            key_limits.append((f"rl:ip:api:{ip}:{minute_bucket}", settings.rate_limit_api_ip_per_minute))
            if org_id:
                key_limits.append((f"rl:tenant:api:{org_id}:{minute_bucket}", settings.rate_limit_api_tenant_per_minute))

        try:
            redis = get_redis_pool()
            for key, limit in key_limits:
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, 120)
                if count > limit:
                    log.warning("rate_limit.blocked", key=key, count=count, limit=limit, path=path)
                    response = JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded",
                            "path": path,
                        },
                    )
                    response.headers["Retry-After"] = "60"
                    _apply_security_headers(response)
                    return response
        except Exception as e:
            log.warning("rate_limit.redis_unavailable", error=str(e))

        response = await call_next(request)
        _apply_security_headers(response)
        return response
