from app.core.observability import (
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
