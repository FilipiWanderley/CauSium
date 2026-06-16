"""
Unit tests for savings_evidence_builder subscription-level handling.

Tests that subscription-level recommendations (Savings Plans, Reserved Instances)
generate correct savings evidence without inventing data.
"""
from __future__ import annotations

import pytest
from uuid import uuid4

from app.domains.decision_engine.savings_evidence_builder import build_savings_evidence
from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    RiskLevel,
)


class MockOpportunity:
    """Mock opportunity for testing build_savings_evidence."""

    def __init__(
        self,
        category: OpportunityCategory = OpportunityCategory.RESERVED_INSTANCES,
        current_monthly_cost_usd: float = 0.0,
        estimated_monthly_savings_usd: float = 150.0,
        risk_level: RiskLevel = RiskLevel.LOW,
        decision_evidence: dict | None = None,
    ):
        self.id = uuid4()
        self.category = category
        self.current_monthly_cost_usd = current_monthly_cost_usd
        self.estimated_monthly_savings_usd = estimated_monthly_savings_usd
        self.risk_level = risk_level
        self.decision_evidence = decision_evidence or {}


class TestSavingsEvidenceSubscriptionLevel:
    """Tests for savings evidence building for subscription-level opportunities."""

    def test_advisor_subscription_level_without_current_spend(self):
        """Should NOT invent current_cost when Advisor does not provide currentSpend."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=150.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
                "advisor_description": "Buy Savings Plan to save money",
                "advisor_impact": "Medium",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert result.current_monthly_cost_estimate == 0.0
        assert result.projected_monthly_cost_estimate is None  # Do NOT invent
        assert result.estimated_monthly_savings == 150.0
        assert "subscription-level" in result.evidence_summary.lower()

    def test_advisor_subscription_level_with_current_spend(self):
        """Should use currentSpend when Advisor provides it."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=150.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
                "current_spend": 5000.0,
                "advisor_description": "Buy Savings Plan to save money",
                "advisor_impact": "Medium",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert result.current_monthly_cost_estimate == 5000.0
        assert result.projected_monthly_cost_estimate == 4850.0
        assert result.estimated_monthly_savings == 150.0

    def test_advisor_subscription_level_methodology(self):
        """Should use azure_advisor methodology for subscription-level."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=150.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
                "advisor_description": "Buy Savings Plan",
                "advisor_impact": "High",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert result.methodology == "azure_advisor"
        assert result.safety_margin_applied is False

    def test_advisor_subscription_level_evidence_summary(self):
        """Should generate explanatory evidence_summary for subscription-level."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=150.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
                "advisor_description": "Consider buying a savings plan",
                "advisor_impact": "Medium",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert "150" in result.evidence_summary
        assert "subscription-level" in result.evidence_summary.lower()

    def test_advisor_subscription_level_limitations(self):
        """Should include subscription-level limitation."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=150.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
                "advisor_description": "Buy Savings Plan",
                "advisor_impact": "Medium",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert any("subscription-level" in lim.lower() for lim in result.limitations)

    def test_advisor_resource_level_with_current_spend(self):
        """Resource-level Advisor recommendations should work as before."""
        opp = MockOpportunity(
            category=OpportunityCategory.RIGHTSIZING,
            current_monthly_cost_usd=1000.0,
            estimated_monthly_savings_usd=300.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": False,
                "current_spend": 1000.0,
                "advisor_description": "Resize VM",
                "advisor_impact": "High",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert result.current_monthly_cost_estimate == 1000.0
        assert result.projected_monthly_cost_estimate == 700.0
        assert "subscription-level" not in result.evidence_summary.lower()

    def test_zero_savings_and_zero_cost_returns_none(self):
        """Should return None when no savings and no cost."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=0.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
            }
        )

        result = build_savings_evidence(opp)

        assert result is None

    def test_only_savings_without_cost_returns_evidence(self):
        """Should return evidence when there are savings but no cost (subscription-level)."""
        opp = MockOpportunity(
            category=OpportunityCategory.RESERVED_INSTANCES,
            current_monthly_cost_usd=0.0,
            estimated_monthly_savings_usd=200.0,
            decision_evidence={
                "source": "azure_advisor",
                "is_subscription_level": True,
                "advisor_description": "Buy Savings Plan",
                "advisor_impact": "High",
            }
        )

        result = build_savings_evidence(opp)

        assert result is not None
        assert result.estimated_monthly_savings == 200.0
        assert result.estimated_annual_savings == 2400.0
