"""
Unit tests for SP-A05 — security headers hardening.

Covers:
  - _apply_security_headers: presence/values for all 10 headers
  - is_api_path=True adds Cache-Control: no-store
  - is_api_path=False does NOT add Cache-Control
  - HSTS absent in non-production, present in production
  - HSTS value driven by hsts_max_age setting
  - validate_production_security: rejects weak secret_key, disabled headers,
    missing upgrade-insecure-requests in CSP, low hsts_max_age
  - hsts_header_value property format
  - Permissions-Policy and CSP driven from settings (not hardcoded)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import Response

from app.core.middleware import _apply_security_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response() -> Response:
    r = Response(content="ok", media_type="text/plain")
    return r


def _mock_settings(
    *,
    enabled: bool = True,
    is_production: bool = False,
    csp: str = "default-src 'self'; upgrade-insecure-requests",
    permissions_policy: str = "geolocation=()",
    hsts_max_age: int = 31_536_000,
):
    s = MagicMock()
    s.security_headers_enabled = enabled
    s.is_production = is_production
    s.csp_policy = csp
    s.permissions_policy = permissions_policy
    s.hsts_max_age = hsts_max_age
    s.hsts_header_value = f"max-age={hsts_max_age}; includeSubDomains"
    return s


# ---------------------------------------------------------------------------
# Header presence — non-production
# ---------------------------------------------------------------------------

def test_x_content_type_options_nosniff(tmp_path):
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["x-content-type-options"] == "nosniff"


def test_x_frame_options_deny():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["x-frame-options"] == "DENY"


def test_referrer_policy():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_coop_same_origin():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["cross-origin-opener-policy"] == "same-origin"


def test_corp_same_site():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["cross-origin-resource-policy"] == "same-site"


def test_coep_require_corp():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["cross-origin-embedder-policy"] == "require-corp"


def test_x_permitted_cross_domain_policies_none():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp)
    assert resp.headers["x-permitted-cross-domain-policies"] == "none"


def test_permissions_policy_from_settings():
    custom = "geolocation=(), microphone=()"
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(permissions_policy=custom)):
        _apply_security_headers(resp)
    assert resp.headers["permissions-policy"] == custom


def test_csp_from_settings():
    custom_csp = "default-src 'self'; upgrade-insecure-requests"
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(csp=custom_csp)):
        _apply_security_headers(resp)
    assert resp.headers["content-security-policy"] == custom_csp


# ---------------------------------------------------------------------------
# Cache-Control header behaviour
# ---------------------------------------------------------------------------

def test_cache_control_no_store_on_api_path():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp, is_api_path=True)
    assert resp.headers["cache-control"] == "no-store"


def test_cache_control_absent_on_non_api_path():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings()):
        _apply_security_headers(resp, is_api_path=False)
    assert "cache-control" not in resp.headers


# ---------------------------------------------------------------------------
# HSTS — present only in production
# ---------------------------------------------------------------------------

def test_hsts_absent_in_development():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(is_production=False)):
        _apply_security_headers(resp)
    assert "strict-transport-security" not in resp.headers


def test_hsts_present_in_production():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(is_production=True)):
        _apply_security_headers(resp)
    assert "strict-transport-security" in resp.headers


def test_hsts_value_contains_max_age_and_subdomain():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(is_production=True, hsts_max_age=63_072_000)):
        _apply_security_headers(resp)
    hsts = resp.headers["strict-transport-security"]
    assert "max-age=63072000" in hsts
    assert "includeSubDomains" in hsts


def test_hsts_does_not_contain_preload_by_default():
    """'preload' must NOT appear until the domain is explicitly registered."""
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(is_production=True)):
        _apply_security_headers(resp)
    assert "preload" not in resp.headers.get("strict-transport-security", "")


# ---------------------------------------------------------------------------
# Headers disabled
# ---------------------------------------------------------------------------

def test_no_headers_when_disabled():
    resp = _make_response()
    with patch("app.core.middleware.get_settings", return_value=_mock_settings(enabled=False)):
        _apply_security_headers(resp)
    assert "x-content-type-options" not in resp.headers
    assert "content-security-policy" not in resp.headers


# ---------------------------------------------------------------------------
# validate_production_security — security enforcement at startup
# ---------------------------------------------------------------------------

def _prod_settings(**overrides):
    from app.core.config import Settings
    base = dict(
        app_env="production",
        secret_key="a-very-long-secret-key-for-production-use",
        database_url="postgresql+asyncpg://u:p@host/db?sslmode=require",
        redis_url="rediss://localhost:6379/0",
        clickhouse_secure=True,
        security_headers_enabled=True,
        hsts_max_age=31_536_000,
        csp_policy="default-src 'self'; upgrade-insecure-requests",
        force_secure_datastores_in_production=True,
    )
    base.update(overrides)
    return Settings(**base)


def test_validate_passes_with_correct_production_config():
    s = _prod_settings()
    s.validate_production_security()  # must not raise


def test_validate_rejects_default_secret_key():
    s = _prod_settings(secret_key="change-me-in-production-at-least-32-chars")
    with pytest.raises(ValueError, match="SECRET_KEY must be changed"):
        s.validate_production_security()


def test_validate_rejects_short_secret_key():
    s = _prod_settings(secret_key="tooshort")
    with pytest.raises(ValueError, match="at least 32 characters"):
        s.validate_production_security()


def test_validate_rejects_disabled_security_headers():
    s = _prod_settings(security_headers_enabled=False)
    with pytest.raises(ValueError, match="SECURITY_HEADERS_ENABLED"):
        s.validate_production_security()


def test_validate_rejects_missing_upgrade_insecure_requests():
    s = _prod_settings(csp_policy="default-src 'self'")
    with pytest.raises(ValueError, match="upgrade-insecure-requests"):
        s.validate_production_security()


def test_validate_rejects_low_hsts_max_age():
    s = _prod_settings(hsts_max_age=3600)
    with pytest.raises(ValueError, match="HSTS_MAX_AGE"):
        s.validate_production_security()


def test_validate_skips_all_checks_in_development():
    from app.core.config import Settings
    s = Settings(
        app_env="development",
        secret_key="short",
        security_headers_enabled=False,
        force_secure_datastores_in_production=True,
    )
    s.validate_production_security()  # must not raise in dev


# ---------------------------------------------------------------------------
# hsts_header_value property
# ---------------------------------------------------------------------------

def test_hsts_header_value_format():
    from app.core.config import Settings
    s = Settings(hsts_max_age=63_072_000)
    assert s.hsts_header_value == "max-age=63072000; includeSubDomains"


def test_hsts_header_value_default():
    from app.core.config import Settings
    s = Settings()
    assert s.hsts_header_value == "max-age=31536000; includeSubDomains"
