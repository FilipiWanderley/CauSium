import pytest

from app.domains.decision_engine.models import EffortLevel, OpportunityCategory, RiskLevel
from app.domains.decision_engine.scorer import WEIGHTS, compute_score


def test_score_range():
    result = compute_score(
        category=OpportunityCategory.IDLE_RESOURCES,
        monthly_savings_usd=500,
        environment="production",
    )
    assert 0 <= result.composite_score <= 100


def test_idle_resources_low_risk():
    result = compute_score(OpportunityCategory.IDLE_RESOURCES, 1000)
    assert result.risk_level == RiskLevel.LOW
    assert result.effort_level == EffortLevel.LOW


def test_architecture_change_high_risk():
    result = compute_score(OpportunityCategory.ARCHITECTURE_CHANGE, 1000)
    assert result.risk_level == RiskLevel.HIGH
    assert result.effort_level == EffortLevel.HIGH


def test_production_higher_than_dev():
    prod = compute_score(OpportunityCategory.RIGHTSIZING, 500, environment="production")
    dev = compute_score(OpportunityCategory.RIGHTSIZING, 500, environment="development")
    assert prod.composite_score > dev.composite_score


def test_higher_savings_higher_score():
    low = compute_score(OpportunityCategory.IDLE_RESOURCES, 100)
    high = compute_score(OpportunityCategory.IDLE_RESOURCES, 2000)
    assert high.financial_impact_score > low.financial_impact_score
    assert high.composite_score > low.composite_score


def test_score_capped_at_100():
    result = compute_score(
        OpportunityCategory.IDLE_RESOURCES,
        monthly_savings_usd=999_999,
        environment="production",
    )
    assert result.composite_score <= 100
    assert result.financial_impact_score <= 100


def test_rationale_contains_key_info():
    result = compute_score(OpportunityCategory.RIGHTSIZING, 300, environment="staging")
    assert "Financial impact" in result.rationale
    assert "Risk" in result.rationale
    assert "Effort" in result.rationale
    assert "Composite" in result.rationale


def test_override_risk_and_effort():
    result = compute_score(
        OpportunityCategory.ARCHITECTURE_CHANGE,
        monthly_savings_usd=1000,
        override_risk=RiskLevel.LOW,
        override_effort=EffortLevel.LOW,
    )
    assert result.risk_level == RiskLevel.LOW
    assert result.effort_level == EffortLevel.LOW


def test_weights_sum_to_one():
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9
