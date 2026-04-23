from __future__ import annotations

from datetime import date

from app.domains.intel.anomaly_detection_service import detect_cost_anomaly_signal


def test_detect_cost_anomaly_signal_detects_spike():
    signal = detect_cost_anomaly_signal(
        provider="aws",
        service="Amazon EC2",
        observed_date=date(2026, 4, 15),
        current_cost_usd=127.0,
        history_costs_usd=[100.0] * 14,
        z_threshold=2.5,
        min_delta_usd=10.0,
        window_days=14,
    )

    assert signal is not None
    assert signal.provider == "aws"
    assert signal.service == "Amazon EC2"
    assert signal.deviation_pct == 27.0
    assert signal.z_score >= 2.5


def test_detect_cost_anomaly_signal_ignores_small_delta():
    signal = detect_cost_anomaly_signal(
        provider="aws",
        service="Amazon S3",
        observed_date=date(2026, 4, 15),
        current_cost_usd=51.0,
        history_costs_usd=[50.0] * 14,
        z_threshold=2.5,
        min_delta_usd=10.0,
        window_days=14,
    )

    assert signal is None
