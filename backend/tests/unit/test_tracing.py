"""Unit tests for app.core.tracing (SP-OP06).

Validates no-op mode, idempotent setup, trace context extraction, and graceful
shutdown — without needing a live OTLP collector or network connectivity.
"""
from __future__ import annotations

import importlib

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


def _reload_tracing():
    """Return a freshly reloaded tracing module with clean global state."""
    import app.core.tracing as mod
    importlib.reload(mod)
    return mod


class TestSetupTracing:
    def test_no_op_mode_does_not_raise(self):
        mod = _reload_tracing()
        mod.setup_tracing(service_name="test-svc", otlp_endpoint="", sample_ratio=1.0)
        assert mod._provider is not None

    def test_provider_is_tracer_provider(self):
        mod = _reload_tracing()
        mod.setup_tracing()
        assert isinstance(mod._provider, TracerProvider)

    def test_idempotent_setup(self):
        mod = _reload_tracing()
        mod.setup_tracing(service_name="first")
        first_provider = mod._provider
        mod.setup_tracing(service_name="second")  # Must be ignored
        assert mod._provider is first_provider

    def test_sample_ratio_clamped_below_zero(self):
        mod = _reload_tracing()
        # Must not raise; ratio clamped to 0.0
        mod.setup_tracing(sample_ratio=-0.5)

    def test_sample_ratio_clamped_above_one(self):
        mod = _reload_tracing()
        # Must not raise; ratio clamped to 1.0
        mod.setup_tracing(sample_ratio=1.5)


class TestShutdownTracing:
    def test_shutdown_clears_provider(self):
        mod = _reload_tracing()
        mod.setup_tracing()
        assert mod._provider is not None
        mod.shutdown_tracing()
        assert mod._provider is None

    def test_shutdown_idempotent_when_already_none(self):
        mod = _reload_tracing()
        mod.shutdown_tracing()  # Provider is None — must not raise
        mod.shutdown_tracing()  # Second call — must not raise


class TestGetTraceContext:
    def test_returns_empty_outside_span(self):
        """Outside an active span, get_trace_context() returns {}."""
        mod = _reload_tracing()
        mod.setup_tracing()
        ctx = mod.get_trace_context()
        assert ctx == {}

    def test_returns_ids_inside_span(self):
        """Inside an active span, returns otel_trace_id and otel_span_id."""
        mod = _reload_tracing()
        mod.setup_tracing()
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            ctx = mod.get_trace_context()
        assert "otel_trace_id" in ctx
        assert "otel_span_id" in ctx
        assert len(ctx["otel_trace_id"]) == 32   # 128-bit hex
        assert len(ctx["otel_span_id"]) == 16    # 64-bit hex

    def test_trace_id_is_valid_hex(self):
        mod = _reload_tracing()
        mod.setup_tracing()
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("hex-check"):
            ctx = mod.get_trace_context()
        # Must be parseable as hexadecimal
        int(ctx["otel_trace_id"], 16)
        int(ctx["otel_span_id"], 16)


@pytest.mark.asyncio
async def test_metrics_endpoint_still_works_after_tracing_setup():
    """Ensure the /metrics endpoint is unaffected by tracing initialisation."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "api_requests_total" in resp.text


@pytest.mark.asyncio
async def test_metrics_requires_internal_key_in_production(monkeypatch):
    """In production, /metrics must require X-Internal-Key matching env secret."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_MONITORING_KEY", "top-secret-key")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.get("/metrics")
        wrong = await client.get("/metrics", headers={"X-Internal-Key": "wrong-key"})
        ok = await client.get("/metrics", headers={"X-Internal-Key": "top-secret-key"})

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert ok.status_code == 200
    assert "api_requests_total" in ok.text


@pytest.mark.asyncio
async def test_metrics_blocked_if_monitoring_key_missing_in_production(monkeypatch):
    """If INTERNAL_MONITORING_KEY is absent in production, /metrics stays forbidden."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("INTERNAL_MONITORING_KEY", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_health_detailed_requires_internal_key_via_environment_flag(monkeypatch):
    """ENVIRONMENT=production must protect /health/detailed the same as APP_ENV."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INTERNAL_MONITORING_KEY", "top-secret-key")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/detailed")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_health_remains_public_in_production(monkeypatch):
    """Basic /health endpoint must remain public even in production."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_MONITORING_KEY", "top-secret-key")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_x_trace_id_header_present_in_response():
    """Every API response must carry an X-Trace-ID header."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert "x-trace-id" in resp.headers


@pytest.mark.asyncio
async def test_x_trace_id_propagated_from_request():
    """When the caller sends X-Trace-ID, it must be echoed back."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    custom_trace_id = "my-custom-trace-abc123"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Trace-ID": custom_trace_id})
    assert resp.headers.get("x-trace-id") == custom_trace_id
