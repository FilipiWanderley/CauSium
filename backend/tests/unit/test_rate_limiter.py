"""
Unit tests for rate limiter helpers (SP-A03).

These tests run entirely in-process using mocks — no Redis or HTTP server
required. They cover:
  - _extract_real_ip: proxy header parsing (XFF, custom headers, fallback)
  - _email_to_key: determinism and injection-resistance
  - _check_sliding_window: blocked/pass/remaining logic via mocked Redis eval
  - _extract_login_email: safe body parsing
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.middleware import (
    _check_sliding_window,
    _email_to_key,
    _extract_login_email,
    _extract_real_ip,
)


# ---------------------------------------------------------------------------
# _extract_real_ip
# ---------------------------------------------------------------------------

def _make_request(*, xff: str | None = None, client_host: str = "10.0.0.1") -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = client_host
    req.headers = {}
    if xff is not None:
        req.headers = {"x-forwarded-for": xff}
    req.headers = MagicMock()
    req.headers.get = lambda k, default="": (xff if k.lower() == "x-forwarded-for" and xff is not None else default)
    return req


def test_extract_real_ip_uses_xff_first_entry():
    req = _make_request(xff="1.2.3.4, 10.0.0.2, 10.0.0.3", client_host="10.0.0.3")
    assert _extract_real_ip(req, "X-Forwarded-For") == "1.2.3.4"


def test_extract_real_ip_single_xff():
    req = _make_request(xff="203.0.113.5", client_host="10.0.0.1")
    assert _extract_real_ip(req, "X-Forwarded-For") == "203.0.113.5"


def test_extract_real_ip_falls_back_when_header_empty():
    req = _make_request(xff="", client_host="192.168.1.100")
    assert _extract_real_ip(req, "X-Forwarded-For") == "192.168.1.100"


def test_extract_real_ip_falls_back_when_no_trusted_header():
    req = _make_request(xff="1.2.3.4", client_host="192.168.1.1")
    # trusted_header is empty string — header must be ignored
    assert _extract_real_ip(req, "") == "192.168.1.1"


def test_extract_real_ip_returns_unknown_when_no_client():
    req = MagicMock()
    req.client = None
    req.headers = MagicMock()
    req.headers.get = lambda k, default="": default
    assert _extract_real_ip(req, "") == "unknown"


def test_extract_real_ip_strips_whitespace():
    req = _make_request(xff="  5.6.7.8  , 10.0.0.1", client_host="10.0.0.1")
    assert _extract_real_ip(req, "X-Forwarded-For") == "5.6.7.8"


# ---------------------------------------------------------------------------
# _email_to_key
# ---------------------------------------------------------------------------

def test_email_to_key_is_deterministic():
    assert _email_to_key("user@example.com") == _email_to_key("user@example.com")


def test_email_to_key_different_emails_differ():
    assert _email_to_key("a@example.com") != _email_to_key("b@example.com")


def test_email_to_key_length():
    # Always 24 hex chars regardless of input length
    assert len(_email_to_key("x@y.com")) == 24
    assert len(_email_to_key("very.long.email.address@extremely.long.domain.example.com")) == 24


def test_email_to_key_no_colon_or_special():
    key = _email_to_key("admin@test.com:0")  # injection attempt
    assert ":" not in key
    assert "@" not in key


# ---------------------------------------------------------------------------
# _check_sliding_window
# ---------------------------------------------------------------------------

def _make_redis_eval_mock(result: list) -> AsyncMock:
    """Return an async mock Redis whose .eval() returns `result`."""
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=result)
    return redis


@pytest.mark.asyncio
async def test_sliding_window_pass_returns_not_blocked():
    redis = _make_redis_eval_mock([3, 7, 0])  # count=3, remaining=7, blocked=0
    blocked, remaining, reset_at = await _check_sliding_window(redis, "rl:test:key", limit=10, window=60)

    assert not blocked
    assert remaining == 7
    assert reset_at > int(time.time())


@pytest.mark.asyncio
async def test_sliding_window_blocked_returns_blocked():
    redis = _make_redis_eval_mock([12, 0, 1])  # count=12, remaining=0, blocked=1
    blocked, remaining, reset_at = await _check_sliding_window(redis, "rl:test:key", limit=10, window=60)

    assert blocked
    assert remaining == 0


@pytest.mark.asyncio
async def test_sliding_window_eval_called_with_two_keys():
    redis = _make_redis_eval_mock([1, 9, 0])
    await _check_sliding_window(redis, "rl:ns:abc", limit=10, window=60)

    call_args = redis.eval.call_args
    # numkeys must be 2
    assert call_args[0][1] == 2
    # Key prefixes must use the same namespace
    assert call_args[0][2].startswith("rl:ns:abc:")
    assert call_args[0][3].startswith("rl:ns:abc:")


@pytest.mark.asyncio
async def test_sliding_window_reset_at_is_future():
    redis = _make_redis_eval_mock([1, 9, 0])
    _, _, reset_at = await _check_sliding_window(redis, "rl:test", limit=10, window=60)
    assert reset_at > int(time.time())


@pytest.mark.asyncio
async def test_sliding_window_reset_at_within_two_windows():
    redis = _make_redis_eval_mock([1, 9, 0])
    window = 60
    _, _, reset_at = await _check_sliding_window(redis, "rl:test", limit=10, window=window)
    now = int(time.time())
    assert reset_at <= now + window * 2


@pytest.mark.asyncio
async def test_sliding_window_window_passed_to_lua():
    redis = _make_redis_eval_mock([1, 9, 0])
    await _check_sliding_window(redis, "rl:test", limit=5, window=30)

    call_args = redis.eval.call_args
    # ARGV[1]=limit, ARGV[2]=weight, ARGV[3]=window
    assert call_args[0][4] == 5    # limit
    assert call_args[0][6] == 30   # window


# ---------------------------------------------------------------------------
# _extract_login_email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_login_email_returns_lowercase():
    req = AsyncMock()
    req.body = AsyncMock(return_value=b'{"email": "Alice@Example.COM", "password": "secret"}')
    email = await _extract_login_email(req)
    assert email == "alice@example.com"


@pytest.mark.asyncio
async def test_extract_login_email_missing_key_returns_none():
    req = AsyncMock()
    req.body = AsyncMock(return_value=b'{"username": "alice", "password": "secret"}')
    assert await _extract_login_email(req) is None


@pytest.mark.asyncio
async def test_extract_login_email_invalid_json_returns_none():
    req = AsyncMock()
    req.body = AsyncMock(return_value=b"not json at all")
    assert await _extract_login_email(req) is None


@pytest.mark.asyncio
async def test_extract_login_email_empty_string_returns_none():
    req = AsyncMock()
    req.body = AsyncMock(return_value=b'{"email": "   "}')
    assert await _extract_login_email(req) is None
