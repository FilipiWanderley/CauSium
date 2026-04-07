"""
Unit tests for SP-A07 — TLS context factory (core/tls.py).

Covers:
  - build_ssl_context returns an ssl.SSLContext
  - minimum_version set to TLSv1.3 by default
  - minimum_version set to TLSv1.2 when requested
  - build_ssl_context raises ValueError for unsupported TLS version string
  - build_ssl_context raises FileNotFoundError for non-existent ca_file
  - build_ssl_context with verify=False disables hostname check and CERT_NONE
  - build_ssl_context with system trust store (ca_file=None)
  - maybe_ssl_context returns None when enabled=False
  - maybe_ssl_context returns SSLContext when enabled=True
  - maybe_ssl_context passes through verify / ca_file / min_version
  - validate_production_security rejects db_ssl_min_version != TLSv1.3
  - validate_production_security rejects redis_ssl_min_version != TLSv1.3
  - validate_production_security rejects clickhouse_verify=False
  - validate_production_security rejects clickhouse_ssl_min_version != TLSv1.3
  - All four TLS checks pass when correctly configured
"""
from __future__ import annotations

import ssl
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.tls import build_ssl_context, maybe_ssl_context


# ---------------------------------------------------------------------------
# build_ssl_context — happy path
# ---------------------------------------------------------------------------

class TestBuildSslContextDefaults:
    def test_returns_ssl_context(self):
        ctx = build_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

    def test_default_minimum_version_is_tls13(self):
        ctx = build_ssl_context()
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_3

    def test_verify_true_enables_cert_required(self):
        ctx = build_ssl_context(verify=True)
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_verify_true_enables_hostname_check(self):
        ctx = build_ssl_context(verify=True)
        assert ctx.check_hostname is True


class TestBuildSslContextMinVersion:
    def test_tls13_sets_minimum_version(self):
        ctx = build_ssl_context(min_version="TLSv1.3")
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_3

    def test_tls12_sets_minimum_version(self):
        ctx = build_ssl_context(min_version="TLSv1.2")
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_unsupported_version_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported TLS version 'TLSv1.0'"):
            build_ssl_context(min_version="TLSv1.0")

    def test_unknown_version_string_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported TLS version 'SSL3'"):
            build_ssl_context(min_version="SSL3")


class TestBuildSslContextVerify:
    def test_verify_false_disables_hostname_check(self):
        ctx = build_ssl_context(verify=False)
        assert ctx.check_hostname is False

    def test_verify_false_sets_cert_none(self):
        ctx = build_ssl_context(verify=False)
        assert ctx.verify_mode == ssl.CERT_NONE


class TestBuildSslContextCaFile:
    def test_none_ca_file_uses_system_trust_store(self):
        # Should not raise; system trust store is loaded by default.
        ctx = build_ssl_context(ca_file=None)
        assert isinstance(ctx, ssl.SSLContext)

    def test_missing_ca_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="CA certificate file not found"):
            build_ssl_context(ca_file="/non/existent/ca.pem")

    def test_valid_ca_file_is_loaded(self):
        # Write a minimal (self-signed) PEM cert so the path exists.
        # We only test that the path check passes and a context is returned;
        # OpenSSL cert validation is trusted to the standard library.
        import subprocess, sys

        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as tmp:
            pem_path = tmp.name
            # Generate a throw-away self-signed cert just for the path check.
            # If openssl is not available, fall back to writing a stub file.
            try:
                subprocess.run(
                    [
                        "openssl", "req", "-x509", "-newkey", "rsa:2048",
                        "-keyout", "/dev/null", "-out", pem_path,
                        "-days", "1", "-nodes",
                        "-subj", "/CN=test",
                    ],
                    check=True,
                    capture_output=True,
                )
                ctx = build_ssl_context(ca_file=pem_path)
                assert isinstance(ctx, ssl.SSLContext)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # openssl CLI not available — just write a non-empty stub
                # to verify that FileNotFoundError is NOT raised for existing files.
                Path(pem_path).write_text("stub")
                # A real SSLContext.load_verify_locations would fail here, but
                # we only want to assert that our path-existence guard works.
                # Wrap in try/except for the SSL load error.
                try:
                    build_ssl_context(ca_file=pem_path)
                except ssl.SSLError:
                    pass  # Expected: stub PEM is not valid.
            finally:
                Path(pem_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# maybe_ssl_context
# ---------------------------------------------------------------------------

class TestMaybeSslContext:
    def test_returns_none_when_disabled(self):
        result = maybe_ssl_context(enabled=False)
        assert result is None

    def test_returns_ssl_context_when_enabled(self):
        result = maybe_ssl_context(enabled=True)
        assert isinstance(result, ssl.SSLContext)

    def test_passes_min_version_through(self):
        ctx = maybe_ssl_context(enabled=True, min_version="TLSv1.2")
        assert ctx is not None
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_default_min_version_is_tls13(self):
        ctx = maybe_ssl_context(enabled=True)
        assert ctx is not None
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_3

    def test_passes_verify_false_through(self):
        ctx = maybe_ssl_context(enabled=True, verify=False)
        assert ctx is not None
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_empty_ca_file_treated_as_none(self):
        # empty string must not trigger FileNotFoundError
        ctx = maybe_ssl_context(enabled=True, ca_file="")
        assert isinstance(ctx, ssl.SSLContext)


# ---------------------------------------------------------------------------
# validate_production_security — TLS 1.3 checks
# ---------------------------------------------------------------------------

def _prod_settings(**overrides):
    """Return a Settings-like dict with sane production defaults."""
    defaults = {
        "app_env": "production",
        "secret_key": "a-very-strong-secret-key-for-test-1234",
        "security_headers_enabled": True,
        "database_url": "postgresql+asyncpg://u:p@host/db?sslmode=verify-full",
        "redis_url": "rediss://localhost:6380/0",
        "clickhouse_secure": True,
        "clickhouse_verify": True,
        "csp_policy": "default-src 'self'; upgrade-insecure-requests",
        "hsts_max_age": 31_536_000,
        "force_secure_datastores_in_production": True,
        "db_ssl_min_version": "TLSv1.3",
        "redis_ssl_min_version": "TLSv1.3",
        "clickhouse_ssl_min_version": "TLSv1.3",
    }
    defaults.update(overrides)
    return defaults


class TestValidateProductionSecurityTLS:
    def _make_settings(self, **overrides):
        from app.core.config import Settings

        data = _prod_settings(**overrides)
        return Settings(**data)

    def test_valid_production_config_does_not_raise(self):
        s = self._make_settings()
        s.validate_production_security()  # must not raise

    def test_db_ssl_min_version_not_tls13_raises(self):
        s = self._make_settings(db_ssl_min_version="TLSv1.2")
        with pytest.raises(ValueError, match="DB_SSL_MIN_VERSION must be TLSv1.3"):
            s.validate_production_security()

    def test_redis_ssl_min_version_not_tls13_raises(self):
        s = self._make_settings(redis_ssl_min_version="TLSv1.2")
        with pytest.raises(ValueError, match="REDIS_SSL_MIN_VERSION must be TLSv1.3"):
            s.validate_production_security()

    def test_clickhouse_verify_false_raises(self):
        s = self._make_settings(clickhouse_verify=False)
        with pytest.raises(ValueError, match="CLICKHOUSE_VERIFY must be true"):
            s.validate_production_security()

    def test_clickhouse_ssl_min_version_not_tls13_raises(self):
        s = self._make_settings(clickhouse_ssl_min_version="TLSv1.2")
        with pytest.raises(ValueError, match="CLICKHOUSE_SSL_MIN_VERSION must be TLSv1.3"):
            s.validate_production_security()
