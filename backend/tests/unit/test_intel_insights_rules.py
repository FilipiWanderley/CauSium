from __future__ import annotations

from app.domains.intel.insights_service import IntelInsightsService


def test_intel_insights_recommended_action_prioritizes_high_risk():
    service = IntelInsightsService(None)  # type: ignore[arg-type]
    action = service._build_recommended_action(
        opportunity={
            "service": "Amazon EC2",
            "risk_level": "low",
        },
        risk={
            "service": "Amazon RDS",
            "severity": "high",
        },
        trend={"delta_usd": 100.0},
        language="en",
    )
    assert "RDS" in action
    assert "anomaly" in action.lower()


def test_intel_insights_confidence_increases_with_signals():
    service = IntelInsightsService(None)  # type: ignore[arg-type]
    low = service._confidence_score(
        opportunity=None,
        risk=None,
        trend={"current_7d_total_usd": 0.0, "previous_7d_total_usd": 0.0},
    )
    high = service._confidence_score(
        opportunity={"service": "Amazon EC2"},
        risk={"service": "Amazon RDS"},
        trend={"current_7d_total_usd": 100.0, "previous_7d_total_usd": 100.0},
    )
    assert high > low
