"""
OpenTelemetry distributed tracing for CauSium backend.

Design:
  - Zero overhead when OTEL_EXPORTER_OTLP_ENDPOINT is not set: the SDK is
    initialised with a no-op (non-recording) provider.  No threads, no
    allocations, no I/O in the hot path.
  - W3C TraceContext propagation (traceparent / tracestate) + B3 legacy
    format for compatibility with older collectors.
  - Auto-instruments FastAPI, SQLAlchemy (async), Redis and httpx so all
    I/O paths carry spans without touching business logic.
  - Exports via OTLP/gRPC when OTLP_ENDPOINT is set (default port 4317).
  - Sampler defaults to ParentBased(ALWAYS_ON).  Set OTEL_SAMPLE_RATIO to
    a value in (0, 1) for probabilistic sampling in high-traffic production.
"""
from __future__ import annotations

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased, TraceIdRatioBased
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

log = logging.getLogger(__name__)

_provider: Optional[TracerProvider] = None
_instrumented: bool = False


def setup_tracing(
    *,
    service_name: str = "causium-backend",
    otlp_endpoint: str = "",
    sample_ratio: float = 1.0,
) -> None:
    """Initialise the global OTel tracer provider.

    Call once at application startup (lifespan).  Safe to call multiple times
    (subsequent calls are ignored once the provider is set).

    Args:
        service_name:   Value of the ``service.name`` resource attribute.
        otlp_endpoint:  OTLP/gRPC collector URL, e.g. ``http://jaeger:4317``.
                        When empty, a no-op exporter is used (zero overhead).
        sample_ratio:   Fraction of traces to sample.  1.0 = 100%, 0.1 = 10%.
                        Values outside [0, 1] are clamped.
    """
    global _provider

    if _provider is not None:
        return  # Already configured — idempotent.

    resource = Resource.create({SERVICE_NAME: service_name})

    ratio = max(0.0, min(1.0, sample_ratio))
    sampler = (
        ParentBased(root=TraceIdRatioBased(ratio))
        if ratio < 1.0
        else ParentBased(root=ALWAYS_ON)
    )

    provider = TracerProvider(resource=resource, sampler=sampler)

    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=not otlp_endpoint.startswith("https://"),
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        log.info(
            "tracing: OTLP exporter configured",
            extra={"endpoint": otlp_endpoint, "sample_ratio": ratio},
        )
    else:
        log.info("tracing: no-op (OTEL_EXPORTER_OTLP_ENDPOINT not set)")

    # W3C TraceContext is the primary standard; B3 is kept for legacy collectors.
    set_global_textmap(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            B3MultiFormat(),
        ])
    )

    trace.set_tracer_provider(provider)
    _provider = provider


def instrument_app(app) -> None:  # type: ignore[type-arg]
    """Apply automatic OTel instrumentation.

    Must be called *after* setup_tracing() inside the lifespan context so
    that FastAPIInstrumentor receives a fully configured TracerProvider.
    Idempotent — safe to call from tests that restart the lifespan.

    Excluded paths:
      /health, /metrics — high-frequency probes that add noise without value.
    """
    global _instrumented
    if _instrumented:
        return

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health.*,metrics.*",
        tracer_provider=_provider,
    )
    # Async SQLAlchemy — instruments both Core and ORM sessions.
    SQLAlchemyInstrumentor().instrument(enable_commenter=True)
    # Redis — instruments all commands.
    RedisInstrumentor().instrument()
    # httpx — instruments cloud-provider API calls (Azure, AWS, GCP connectors).
    HTTPXClientInstrumentor().instrument()

    _instrumented = True


def shutdown_tracing() -> None:
    """Flush pending spans and shut down the exporter cleanly on app shutdown."""
    global _provider, _instrumented
    if _provider is not None:
        _provider.shutdown()
        _provider = None
    _instrumented = False


def get_trace_context() -> dict[str, str]:
    """Return the active trace_id and span_id for structlog correlation.

    Returns an empty dict when there is no active span (e.g. background tasks
    that haven't been linked to a trace, or when tracing is in no-op mode).
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return {}
    return {
        "otel_trace_id": format(ctx.trace_id, "032x"),
        "otel_span_id": format(ctx.span_id, "016x"),
    }
