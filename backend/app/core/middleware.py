from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis_pool
from app.core.security import decode_token

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Sliding-window rate limiter — Lua script (atomic, O(1) per call)
#
# Uses two consecutive fixed-size buckets with weighted averaging across the
# window boundary, giving a smooth sliding-window approximation at Redis
# counter cost:
#
#   estimated = floor(prev_count × weight_of_prev_bucket) + curr_count
#
# Because the script runs atomically inside Redis, there are no TOCTOU races.
# ---------------------------------------------------------------------------
_SLIDING_WINDOW_LUA: str = """
local prev   = tonumber(redis.call('GET', KEYS[1])) or 0
local curr   = tonumber(redis.call('GET', KEYS[2])) or 0
local limit  = tonumber(ARGV[1])
local weight = tonumber(ARGV[2])
local window = tonumber(ARGV[3])

local estimated = math.floor(prev * weight) + curr
if estimated >= limit then
    return {estimated, 0, 1}
end

local new_curr = redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], window * 2)
estimated = math.floor(prev * weight) + new_curr
local remaining = math.max(0, limit - estimated)
return {new_curr, remaining, 0}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_real_ip(request: Request, trusted_header: str) -> str:
    """
    Return the real client IP, respecting a configurable reverse-proxy header.

    X-Forwarded-For contains a comma-separated chain:
        client, proxy1, proxy2, …
    We take the leftmost entry (originating client). This is correct when the
    deployment sits behind a single trusted reverse proxy (e.g. nginx) that
    appends the real client IP and we control the chain.
    """
    if trusted_header:
        raw = request.headers.get(trusted_header, "").strip()
        if raw:
            first = raw.split(",", 1)[0].strip()
            if first:
                return first
    return request.client.host if request.client else "unknown"


def _extract_org_id(request: Request) -> str | None:
    """Decode the access token (Bearer or cookie) and return the org_id claim."""
    token: str | None = None

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip() or None

    if not token:
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


async def _extract_login_email(request: Request) -> str | None:
    """
    Safely extract 'email' from a JSON POST body without consuming the stream.

    Starlette caches the body in request._body after the first read, so
    downstream handlers can still access the full payload.
    """
    try:
        body = await request.body()
        data = json.loads(body)
        email = str(data.get("email", "")).strip().lower()
        return email or None
    except Exception:
        return None


def _email_to_key(email: str) -> str:
    """Hash the email for use as a Redis key component to prevent injection."""
    return hashlib.sha256(email.encode()).hexdigest()[:24]


async def _check_sliding_window(
    redis,
    key_prefix: str,
    limit: int,
    window: int,
) -> tuple[bool, int, int]:
    """
    Atomically check and conditionally increment a sliding-window counter.

    Args:
        redis:      An active redis.asyncio client.
        key_prefix: Namespace for the two bucket keys.
        limit:      Maximum number of requests allowed inside `window` seconds.
        window:     Window duration in seconds.

    Returns:
        (is_blocked, remaining, reset_at_epoch)
    """
    now = time.time()
    bucket = int(now // window)
    weight = 1.0 - ((now % window) / window)
    reset_at = int((bucket + 1) * window)

    result = await redis.eval(
        _SLIDING_WINDOW_LUA,
        2,
        f"{key_prefix}:{bucket - 1}",
        f"{key_prefix}:{bucket}",
        limit,
        f"{weight:.6f}",
        window,
    )

    is_blocked = bool(int(result[2]))
    remaining = int(result[1])
    return is_blocked, remaining, reset_at


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


# ---------------------------------------------------------------------------
# Middleware installation
# ---------------------------------------------------------------------------

def install_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Callable):
        settings = get_settings()
        path = request.url.path
        method = request.method

        if not settings.rate_limit_enabled or not path.startswith("/api/"):
            response = await call_next(request)
            _apply_security_headers(response)
            return response

        ip = _extract_real_ip(request, settings.rate_limit_trusted_proxy_header)
        window = settings.rate_limit_window_seconds

        # --- Build per-request rule list (key_prefix, limit) -----------------
        rules: list[tuple[str, int]] = []

        if path == "/api/v1/auth/login" and method == "POST":
            # Tight limit per IP to slow credential-stuffing
            rules.append((f"rl:login:ip:{ip}", settings.rate_limit_auth_login_ip_per_window))
            # Per-email limit to block targeted brute-force; email is hashed
            # to prevent Redis key injection from malicious input.
            email = await _extract_login_email(request)
            if email:
                rules.append((
                    f"rl:login:email:{_email_to_key(email)}",
                    settings.rate_limit_auth_email_per_window,
                ))
        elif path.startswith("/api/v1/auth"):
            rules.append((f"rl:auth:ip:{ip}", settings.rate_limit_auth_ip_per_minute))
        else:
            rules.append((f"rl:api:ip:{ip}", settings.rate_limit_api_ip_per_minute))
            org_id = _extract_org_id(request)
            if org_id:
                rules.append((
                    f"rl:api:tenant:{org_id}",
                    settings.rate_limit_api_tenant_per_minute,
                ))

        # --- Evaluate rules against Redis ------------------------------------
        primary_limit: int = rules[0][1]
        primary_remaining: int = primary_limit
        primary_reset: int = int(time.time()) + window

        try:
            redis = get_redis_pool()
            for idx, (key_prefix, limit) in enumerate(rules):
                blocked, remaining, reset_at = await _check_sliding_window(
                    redis, key_prefix, limit, window
                )
                if idx == 0:
                    primary_limit = limit
                    primary_remaining = remaining
                    primary_reset = reset_at

                if blocked:
                    log.warning(
                        "rate_limit.blocked",
                        key=key_prefix,
                        limit=limit,
                        path=path,
                        ip=ip,
                    )
                    resp = JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Please slow down."},
                    )
                    resp.headers["Retry-After"] = str(window)
                    resp.headers["X-RateLimit-Limit"] = str(limit)
                    resp.headers["X-RateLimit-Remaining"] = "0"
                    resp.headers["X-RateLimit-Reset"] = str(reset_at)
                    _apply_security_headers(resp)
                    return resp

        except Exception as exc:
            # Redis unavailable — fail open to avoid cascading outage.
            # The error is logged; requests are served without rate limiting.
            log.error("rate_limit.redis_error", error=str(exc))

        response = await call_next(request)
        _apply_security_headers(response)
        response.headers["X-RateLimit-Limit"] = str(primary_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, primary_remaining))
        response.headers["X-RateLimit-Reset"] = str(primary_reset)
        return response
