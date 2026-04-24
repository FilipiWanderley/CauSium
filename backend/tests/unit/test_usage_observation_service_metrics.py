from __future__ import annotations

from datetime import datetime, timezone

from app.domains.intel import usage_observation_service as service_module
from app.domains.intel.usage_observation_service import UsageObservationService


def test_metrics_list_includes_cpu_and_memory_aliases():
    metric_names = set(service_module._METRICS)
    assert "Percentage CPU" in metric_names
    assert "CPUUtilization" in metric_names
    assert "Memory Percentage" in metric_names
    assert "MemoryUtilization" in metric_names


def test_fetch_usage_stats_passes_cpu_and_memory_metric_filters(monkeypatch):
    captured_params: dict = {}

    def _fake_execute_query(query, params):
        captured_params.update(params)
        return []

    monkeypatch.setattr(service_module, "execute_query", _fake_execute_query)

    svc = UsageObservationService(db=None)  # type: ignore[arg-type]
    out = svc._fetch_usage_stats(
        org_id="org-1",
        account_id="acc-1",
        window_start=datetime(2026, 4, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 4, 2, tzinfo=timezone.utc),
    )

    assert out == []
    metric_names = set(captured_params["metric_names"])
    assert "Percentage CPU" in metric_names
    assert "Memory Percentage" in metric_names
