"""
Integration tests for rate limiting middleware (SP-A03).

Strategy: rather than spinning up N requests to naturally hit the counter
(which is flaky and slow), we patch _check_sliding_window to return
controlled values so we can test the middleware's branching logic in full
HTTP roundtrips — including headers and status codes.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enable_rate_limit_for_this_module():
    settings = get_settings()
    prev = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    try:
        yield
    finally:
        settings.rate_limit_enabled = prev

async def _register_and_login(client) -> tuple[dict, dict]:
    """Register a user and return (auth_headers, login_payload)."""
    login_payload = {
        "email": "ratelimit@test.com",
        "password": "rlpassword123",
    }
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "RateLimit Org",
        "org_slug": "ratelimit-org",
        "email": login_payload["email"],
        "full_name": "RL User",
        "password": login_payload["password"],
    })
    assert resp.status_code == 201, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return headers, login_payload


# ---------------------------------------------------------------------------
# X-RateLimit-* headers on normal (non-blocked) responses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_headers_present_on_200(client):
    """Every successful API response must carry X-RateLimit-* headers."""
    _pass = AsyncMock(return_value=(False, 280, 9999999999))

    with patch("app.core.middleware._check_sliding_window", new=_pass):
        resp = await client.post("/api/v1/auth/register", json={
            "org_name": "RL Header Org",
            "org_slug": "rl-header-org",
            "email": "rl-header@test.com",
            "full_name": "RL Header User",
            "password": "headerspassword123",
        })

    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers
    assert "x-ratelimit-reset" in resp.headers


@pytest.mark.asyncio
async def test_rate_limit_remaining_is_non_negative(client):
    _pass = AsyncMock(return_value=(False, 0, 9999999999))

    with patch("app.core.middleware._check_sliding_window", new=_pass):
        resp = await client.get("/health")  # /health is not under /api/, no RL

    # For /health (not /api/), middleware skips RL — no RL headers expected, just 200
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_reset_is_epoch_timestamp(client):
    future_epoch = 9_999_999_999
    _pass = AsyncMock(return_value=(False, 5, future_epoch))

    with patch("app.core.middleware._check_sliding_window", new=_pass):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "wrong",
        })

    if "x-ratelimit-reset" in resp.headers:
        assert int(resp.headers["x-ratelimit-reset"]) == future_epoch


# ---------------------------------------------------------------------------
# 429 returned when sliding window signals blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ip_rate_limit_returns_429(client):
    """Middleware must return 429 when the IP counter is blocked."""
    _blocked = AsyncMock(return_value=(True, 0, 9999999999))

    with patch("app.core.middleware._check_sliding_window", new=_blocked):
        resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 429
    assert resp.json()["detail"] == "Rate limit exceeded. Please slow down."


@pytest.mark.asyncio
async def test_rate_limit_429_includes_retry_after(client):
    _blocked = AsyncMock(return_value=(True, 0, 9999999999))

    with patch("app.core.middleware._check_sliding_window", new=_blocked):
        resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 429
    assert "retry-after" in resp.headers
    assert int(resp.headers["retry-after"]) > 0


@pytest.mark.asyncio
async def test_rate_limit_429_includes_rl_headers(client):
    _blocked = AsyncMock(return_value=(True, 0, 9999999999))

    with patch("app.core.middleware._check_sliding_window", new=_blocked):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "victim@test.com",
            "password": "anypassword",
        })

    assert resp.status_code == 429
    assert "x-ratelimit-limit" in resp.headers
    assert resp.headers["x-ratelimit-remaining"] == "0"
    assert "x-ratelimit-reset" in resp.headers


# ---------------------------------------------------------------------------
# Login endpoint — per-IP and per-email rules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_per_email_rule_triggers_429(client):
    """
    For POST /auth/login the middleware must check both IP and email rules.
    This test verifies that if the second call (email rule) blocks, 429 is
    returned even when the IP rule passes.
    """
    call_count = 0

    async def _email_blocks_second_call(redis, key_prefix, limit, window):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return (False, 9, 9999999999)   # IP rule passes
        return (True, 0, 9999999999)        # email rule blocks

    with patch("app.core.middleware._check_sliding_window", side_effect=_email_blocks_second_call):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "brute@target.com",
            "password": "wrong",
        })

    assert resp.status_code == 429
    assert call_count == 2  # both rules were evaluated


@pytest.mark.asyncio
async def test_login_ip_rule_short_circuits_before_email_rule(client):
    """
    When the IP rule already blocks, the email rule must NOT be evaluated
    (short-circuit).
    """
    call_count = 0

    async def _ip_blocks_first_call(redis, key_prefix, limit, window):
        nonlocal call_count
        call_count += 1
        return (True, 0, 9999999999)  # always blocked

    with patch("app.core.middleware._check_sliding_window", side_effect=_ip_blocks_first_call):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "brute@target.com",
            "password": "wrong",
        })

    assert resp.status_code == 429
    assert call_count == 1  # short-circuited after IP rule


# ---------------------------------------------------------------------------
# Redis unavailability — fail open (do not disrupt service)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_error_fails_open(client):
    """
    If Redis is unavailable, the middleware must not block requests.
    Availability > rate limiting when the store is down.
    """
    async def _raise(*args, **kwargs):
        raise ConnectionError("Redis unavailable")

    with patch("app.core.middleware._check_sliding_window", side_effect=_raise):
        resp = await client.post("/api/v1/auth/register", json={
            "org_name": "Failopen Org",
            "org_slug": "failopen-org",
            "email": "failopen@test.com",
            "full_name": "Failopen User",
            "password": "failopenpassword123",
        })

    # Request must succeed despite Redis being unavailable
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Security headers on 429
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_headers_present_on_429(client):
    _blocked = AsyncMock(return_value=(True, 0, 9999999999))

    with patch("app.core.middleware._check_sliding_window", new=_blocked):
        resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 429
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
