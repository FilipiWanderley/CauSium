from __future__ import annotations

from app.domains.intel.llm_service import _coerce_recommendation_out, _mock_explain_recommendation


def test_coerce_recommendation_out_bounds_confidence_and_lists():
    out = _coerce_recommendation_out(
        {
            "summary": "summary",
            "why_now": "why",
            "expected_impact": "impact",
            "risks": ["risk-a", "", "risk-b"],
            "recommended_steps": ["step-1", "step-2"],
            "confidence": 1.4,
        },
        language="en",
    )
    assert out.summary == "summary"
    assert out.confidence == 1.0
    assert out.risks == ["risk-a", "risk-b"]
    assert out.recommended_steps == ["step-1", "step-2"]


def test_mock_explain_recommendation_pt_returns_portuguese_shape():
    out = _mock_explain_recommendation(
        {
            "recommendation": {
                "title": "Rightsize VM",
                "estimated_monthly_savings_usd": 123.45,
            }
        },
        language="pt",
    )
    assert "recomendacao" in out.summary.lower() or "recommendacao" in out.summary.lower()
    assert out.confidence > 0
    assert len(out.recommended_steps) >= 2
