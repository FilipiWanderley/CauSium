import pytest
from httpx import AsyncClient, ASGITransport

from app.core.observability import (
    build_sli_slo_snapshot,
    observe_api_request,
    observe_worker_job,
    observe_worker_lifecycle,
    render_metrics_prometheus,
    sanitize_path,
)


def test_sanitize_path_masks_ids() -> None:
    path = "/api/v1/notifications/123e4567-e89b-12d3-a456-426614174000/events/42"
    assert sanitize_path(path) == "/api/v1/notifications/:id/events/:id"


def test_render_metrics_prometheus_includes_api_and_worker_metrics() -> None:
    observe_api_request("GET", "/api/v1/health/42", 200, 12.5)
    observe_worker_job("economics_export", "success", 78.2)
    observe_worker_lifecycle("economics_export", "started")

    output = render_metrics_prometheus()

    assert "api_requests_total" in output
    assert "worker_jobs_total" in output
    assert "worker_lifecycle_total" in output
    assert 'path="/api/v1/health/:id"' in output
    assert 'worker="economics_export"' in output


@pytest.mark.asyncio
async def test_metrics_slo_endpoint_returns_200() -> None:
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics/slo")
    assert resp.status_code == 200
    body = resp.json()
    assert "global_sli" in body
    assert "api_paths" in body
    assert "alerts" in body
    assert "targets" in body


@pytest.mark.asyncio
async def test_metrics_slo_accepts_query_params() -> None:
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics/slo?error_budget_pct=0.5&api_p95_ms=200")
    assert resp.status_code == 200
    body = resp.json()
    assert body["targets"]["api_error_budget_pct"] == pytest.approx(0.5)
    assert body["targets"]["api_p95_latency_ms"] == pytest.approx(200.0)


def test_build_sli_slo_snapshot_emits_actionable_alerts() -> None:
    for _ in range(40):
        observe_api_request("GET", "/api/v1/unstable", 500, 920.0)
    for _ in range(15):
        observe_worker_job("economics_export", "failed", 320.0)
    for _ in range(5):
        observe_worker_job("economics_export", "success", 80.0)

    snapshot = build_sli_slo_snapshot(error_budget_pct=1.0, api_p95_ms_target=500.0)

    assert snapshot["global_sli"]["requests_total"] >= 40
    assert snapshot["alerts"]
    assert any(alert["scope"] == "api" for alert in snapshot["alerts"])
    assert any(alert["scope"] == "worker" for alert in snapshot["alerts"])
