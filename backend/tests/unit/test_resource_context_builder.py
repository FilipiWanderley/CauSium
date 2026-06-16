"""
Unit tests for resource_context_builder subscription-level handling.

Tests that subscription-level recommendations (Savings Plans, Reserved Instances)
are handled correctly without inventing data.
"""
from __future__ import annotations

from uuid import uuid4

from app.domains.decision_engine.resource_context_builder import (
    is_subscription_level_resource_id,
    build_portal_url,
    parse_arm_resource_id,
    build_resource_context,
)


class TestIsSubscriptionLevelResourceId:
    """Tests for subscription-level resource ID detection."""

    def test_subscription_only_returns_true(self):
        """Subscription-level resource ID should return True."""
        assert is_subscription_level_resource_id("/subscriptions/abc123") is True
        assert is_subscription_level_resource_id("/subscriptions/abc123/def456") is True

    def test_resource_level_returns_false(self):
        """Resource-level resource ID should return False."""
        assert is_subscription_level_resource_id(
            "/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"
        ) is False

    def test_resource_level_with_child_returns_false(self):
        """Child resources should return False."""
        assert is_subscription_level_resource_id(
            "/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/disks/disk1"
        ) is False

    def test_empty_returns_false(self):
        """Empty or None resource_id should return False."""
        assert is_subscription_level_resource_id("") is False
        assert is_subscription_level_resource_id(None) is False

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        assert is_subscription_level_resource_id("/SUBSCRIPTIONS/abc123") is True
        assert is_subscription_level_resource_id("/Subscriptions/abc123") is True


class TestBuildPortalUrlForSubscription:
    """Tests for portal URL generation for subscription-level resources."""

    def test_subscription_level_generates_portal_url(self):
        """Subscription-level resource should generate portal URL."""
        url = build_portal_url("/subscriptions/abc123")
        assert url == "https://portal.azure.com/#resource/subscriptions/abc123"

    def test_subscription_level_with_longer_id(self):
        """Longer subscription IDs should work."""
        url = build_portal_url("/subscriptions/180203f3-abcd-1234-5678-90abcdef1234")
        assert url == "https://portal.azure.com/#resource/subscriptions/180203f3-abcd-1234-5678-90abcdef1234"

    def test_resource_level_generates_portal_url(self):
        """Resource-level resource should generate portal URL."""
        url = build_portal_url(
            "/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"
        )
        assert url == "https://portal.azure.com/#resource/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"

    def test_invalid_resource_id_returns_none(self):
        """Invalid resource IDs should return None."""
        assert build_portal_url("invalid") is None
        assert build_portal_url("") is None
        assert build_portal_url(None) is None

    def test_only_subscriptions_path_returns_none(self):
        """Path without /subscriptions/ should return None."""
        # Invalid Azure resource path (missing /subscriptions/)
        assert build_portal_url("/resourceGroups/rg/providers/Microsoft.Compute/vms/vm1") is None


class TestParseArmResourceId:
    """Tests for ARM resource ID parsing."""

    def test_subscription_only_parsing(self):
        """Subscription-only ID should parse correctly."""
        result = parse_arm_resource_id("/subscriptions/abc123")
        assert result["subscription_id"] == "abc123"
        assert result["resource_group"] is None
        assert result["resource_type"] is None
        assert result["resource_name"] is None
        assert result["provider"] == "azure"

    def test_resource_level_parsing(self):
        """Resource-level ID should parse correctly."""
        result = parse_arm_resource_id(
            "/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"
        )
        assert result["subscription_id"] == "abc"
        assert result["resource_group"] == "rg"
        assert result["resource_type"] == "Microsoft.Compute/virtualMachines"
        assert result["resource_name"] == "vm1"


class MockOpportunity:
    """Mock opportunity for testing build_resource_context."""

    def __init__(
        self,
        resource_id: str | None = None,
        resource_name: str | None = None,
        sku_name: str | None = None,
        machine_family: str | None = None,
        service: str | None = None,
        region: str | None = None,
        environment: str | None = None,
        owner_team: str | None = None,
        decision_evidence: dict | None = None,
    ):
        self.id = uuid4()
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.sku_name = sku_name
        self.machine_family = machine_family
        self.service = service
        self.region = region
        self.environment = environment
        self.owner_team = owner_team
        self.decision_evidence = decision_evidence or {}


class TestBuildResourceContextSubscriptionLevel:
    """Tests for resource context building for subscription-level opportunities."""

    def test_subscription_level_sets_correct_defaults(self):
        """Subscription-level should set resource_type and resource_name correctly."""
        opp = MockOpportunity(
            resource_id="/subscriptions/abc123",
            resource_name=None,
        )
        ctx = build_resource_context(opp)

        assert ctx.resource_type == "Azure Subscription"
        assert ctx.resource_name == "Subscription abc123"
        assert ctx.resource_group is None
        assert ctx.granularity_tier == "subscription"
        assert ctx.portal_url == "https://portal.azure.com/#resource/subscriptions/abc123"

    def test_subscription_level_uses_short_id(self):
        """Subscription-level should use short ID in resource_name."""
        opp = MockOpportunity(
            resource_id="/subscriptions/180203f3-abcd-1234-5678-90abcdef1234",
        )
        ctx = build_resource_context(opp)

        assert ctx.resource_name == "Subscription 180203f3"

    def test_subscription_level_preserves_existing_resource_name(self):
        """If resource_name is provided, use it instead of generating."""
        opp = MockOpportunity(
            resource_id="/subscriptions/abc123",
            resource_name="My Savings Plan",
        )
        ctx = build_resource_context(opp)

        assert ctx.resource_name == "My Savings Plan"

    def test_resource_level_does_not_override_resource_name(self):
        """Resource-level should not override resource_name with Subscription prefix."""
        opp = MockOpportunity(
            resource_id="/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1",
            resource_name="vm-production-01",
        )
        ctx = build_resource_context(opp)

        assert ctx.resource_name == "vm-production-01"
        assert ctx.resource_type == "Microsoft.Compute/virtualMachines"
        assert ctx.granularity_tier == "resource"

    def test_subscription_level_portal_url(self):
        """Subscription-level should generate correct portal URL."""
        opp = MockOpportunity(
            resource_id="/subscriptions/abc123",
        )
        ctx = build_resource_context(opp)

        assert ctx.portal_url == "https://portal.azure.com/#resource/subscriptions/abc123"

    def test_subscription_level_resource_group_is_null(self):
        """Subscription-level should have null resource_group."""
        opp = MockOpportunity(
            resource_id="/subscriptions/abc123",
        )
        ctx = build_resource_context(opp)

        assert ctx.resource_group is None
