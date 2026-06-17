"""
Unit tests for Azure Advisor opportunity title generation with subscription names.

Tests that titles use real subscription names when available,
and fall back to short ID when not available.
"""
from __future__ import annotations

from app.domains.decision_engine.service import _advisor_group_category_title
from app.domains.decision_engine.models import OpportunityCategory


class TestAdvisorGroupCategoryTitle:
    """Tests for _advisor_group_category_title with subscription names."""

    def test_savings_plan_with_subscription_name(self):
        """Savings Plan should use real subscription name in title."""
        category, title = _advisor_group_category_title(
            norm_type="savings_plan",
            subscription_id="180203f3-abcd-1234-5678-90abcdef1234",
            rec_count=1,
            subscription_name="CSC",
        )

        assert category == OpportunityCategory.RESERVED_INSTANCES
        assert title == "Azure Savings Plan for CSC"
        assert "subscription 180203f3" not in title.lower()

    def test_savings_plan_without_subscription_name(self):
        """Savings Plan should fall back to short ID when name not available."""
        category, title = _advisor_group_category_title(
            norm_type="savings_plan",
            subscription_id="180203f3-abcd-1234-5678-90abcdef1234",
            rec_count=1,
            subscription_name=None,
        )

        assert category == OpportunityCategory.RESERVED_INSTANCES
        assert title == "Azure Savings Plan for 180203f3..."

    def test_reserved_instance_with_subscription_name(self):
        """Reserved Instance should use real subscription name in title."""
        category, title = _advisor_group_category_title(
            norm_type="reserved_instance",
            subscription_id="abc12345-def6-7890-abcd-ef1234567890",
            rec_count=1,
            subscription_name="Production Azure",
        )

        assert category == OpportunityCategory.RESERVED_INSTANCES
        assert title == "Reserved Instance coverage for Production Azure"

    def test_reserved_instance_without_subscription_name(self):
        """Reserved Instance should fall back to short ID."""
        category, title = _advisor_group_category_title(
            norm_type="reserved_instance",
            subscription_id="abc12345-def6-7890-abcd-ef1234567890",
            rec_count=1,
            subscription_name=None,
        )

        assert category == OpportunityCategory.RESERVED_INSTANCES
        assert title == "Reserved Instance coverage for abc12345..."

    def test_multiple_options_with_subscription_name(self):
        """Multiple options should show count suffix with subscription name."""
        category, title = _advisor_group_category_title(
            norm_type="savings_plan",
            subscription_id="180203f3-abcd-1234-5678-90abcdef1234",
            rec_count=3,
            subscription_name="CSC",
        )

        assert title == "Azure Savings Plan for CSC (3 options)"

    def test_idle_resources_with_subscription_name(self):
        """Idle resources should use subscription name."""
        category, title = _advisor_group_category_title(
            norm_type="idle_resource",
            subscription_id="180203f3-abcd-1234-5678-90abcdef1234",
            rec_count=1,
            subscription_name="VITAL",
        )

        assert category == OpportunityCategory.IDLE_RESOURCES
        assert title == "Idle resources in VITAL"

    def test_rightsizing_with_subscription_name(self):
        """Rightsizing should use subscription name."""
        category, title = _advisor_group_category_title(
            norm_type="rightsizing",
            subscription_id="180203f3-abcd-1234-5678-90abcdef1234",
            rec_count=2,
            subscription_name="QGSA",
        )

        assert category == OpportunityCategory.RIGHTSIZING
        assert title == "Rightsizing opportunities in QGSA (2 options)"

    def test_unknown_type_with_subscription_name(self):
        """Unknown type should use subscription name."""
        category, title = _advisor_group_category_title(
            norm_type="unknown_type",
            subscription_id="180203f3-abcd-1234-5678-90abcdef1234",
            rec_count=1,
            subscription_name="FRONTIS",
        )

        assert category == OpportunityCategory.ARCHITECTURE_CHANGE
        assert title == "Azure Advisor: cost optimization for FRONTIS"
