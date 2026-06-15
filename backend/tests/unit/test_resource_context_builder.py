"""
Unit tests for Resource Context Builder.

Tests:
- build_portal_url() - Azure Portal URL generation
- parse_arm_resource_id() - ARM resource ID parsing
- build_resource_context() - Resource context enrichment
"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.domains.decision_engine.resource_context_builder import (
    build_portal_url,
    parse_arm_resource_id,
    build_resource_context,
)


# ── TestBuildPortalUrl ─────────────────────────────────────────────────────────


class TestBuildPortalUrl:
    """Tests for Azure Portal URL generation."""

    def test_vm_resource(self):
        """Test portal URL generation for VM resource - exact equality."""
        resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01"
        url = build_portal_url(resource_id)

        assert url is not None
        # Exact equality check
        assert url == (
            "https://portal.azure.com/#resource"
            "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01"
        )
        # Negative checks to prevent regression
        assert "[" not in url
        assert "](" not in url
        assert "%7B" not in url
        assert "%7D" not in url

    def test_subscription_level(self):
        """Test that subscription-only IDs return None."""
        resource_id = "/subscriptions/xxx"
        url = build_portal_url(resource_id)

        assert url is None

    def test_empty_string(self):
        """Test that empty string returns None."""
        url = build_portal_url("")
        assert url is None

    def test_none(self):
        """Test that None returns None."""
        url = build_portal_url(None)
        assert url is None

    def test_lowercase_resourcegroups(self):
        """Test portal URL with lowercase resourceGroups - exact equality."""
        resource_id = "/subscriptions/xxx/resourcegroups/rg/providers/microsoft.compute/virtualmachines/vm-01"
        url = build_portal_url(resource_id)

        assert url is not None
        # Exact equality check
        assert url == (
            "https://portal.azure.com/#resource"
            "/subscriptions/xxx/resourcegroups/rg/providers/microsoft.compute/virtualmachines/vm-01"
        )
        # Negative checks to prevent regression
        assert "[" not in url
        assert "](" not in url
        assert "%7B" not in url
        assert "%7D" not in url

    def test_child_resource(self):
        """Test portal URL for child resources - exact equality."""
        resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Sql/servers/sql-01/databases/db-01"
        url = build_portal_url(resource_id)

        assert url is not None
        # Exact equality check
        assert url == (
            "https://portal.azure.com/#resource"
            "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Sql/servers/sql-01/databases/db-01"
        )
        # Negative checks to prevent regression
        assert "[" not in url
        assert "](" not in url
        assert "%7B" not in url
        assert "%7D" not in url


# ── TestParseArmResourceId ──────────────────────────────────────────────────────


class TestParseArmResourceId:
    """Tests for ARM resource ID parsing."""

    def test_parse_full_resource(self):
        """Test parsing a full Azure resource ID."""
        resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01"
        parsed = parse_arm_resource_id(resource_id)

        assert parsed is not None
        assert parsed["subscription_id"] == "xxx"
        assert parsed["resource_group"] == "rg"
        assert parsed["resource_type"] == "Microsoft.Compute/virtualMachines"
        assert parsed["resource_name"] == "vm-01"
        assert parsed["provider"] == "azure"

    def test_parse_lowercase_resourcegroups(self):
        """Test parsing with lowercase resourceGroups."""
        resource_id = "/subscriptions/xxx/resourcegroups/rg/providers/microsoft.compute/virtualmachines/vm-01"
        parsed = parse_arm_resource_id(resource_id)

        assert parsed is not None
        assert parsed["subscription_id"] == "xxx"
        assert parsed["resource_group"] == "rg"
        assert parsed["resource_type"] == "microsoft.compute/virtualmachines"
        assert parsed["resource_name"] == "vm-01"

    def test_subscription_only(self):
        """Test parsing subscription-only ID."""
        resource_id = "/subscriptions/xxx"
        parsed = parse_arm_resource_id(resource_id)

        assert parsed is not None
        assert parsed["subscription_id"] == "xxx"
        assert parsed["resource_group"] is None
        assert parsed["resource_type"] is None
        assert parsed["resource_name"] is None

    def test_child_resource(self):
        """Test parsing child resource (SQL database)."""
        resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Sql/servers/sql-01/databases/db-01"
        parsed = parse_arm_resource_id(resource_id)

        assert parsed is not None
        assert parsed["subscription_id"] == "xxx"
        assert parsed["resource_group"] == "rg"
        assert parsed["resource_type"] == "Microsoft.Sql/servers/databases"
        assert parsed["resource_name"] == "db-01"

    def test_empty_string(self):
        """Test parsing empty string returns None."""
        parsed = parse_arm_resource_id("")
        assert parsed is None

    def test_none(self):
        """Test parsing None returns None."""
        parsed = parse_arm_resource_id(None)
        assert parsed is None

    def test_invalid_format(self):
        """Test parsing invalid format returns None."""
        parsed = parse_arm_resource_id("not-a-resource-id")
        assert parsed is None

    def test_preserve_original_case(self):
        """Test that original case is preserved in values."""
        resource_id = "/subscriptions/xxx/resourceGroups/RG/providers/Microsoft.Compute/VirtualMachines/VM-01"
        parsed = parse_arm_resource_id(resource_id)

        assert parsed is not None
        assert parsed["resource_group"] == "RG"
        assert parsed["resource_type"] == "Microsoft.Compute/VirtualMachines"
        assert parsed["resource_name"] == "VM-01"

    def test_disk_resource(self):
        """Test parsing disk resource ID."""
        resource_id = "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-01"
        parsed = parse_arm_resource_id(resource_id)

        assert parsed is not None
        assert parsed["resource_group"] == "rg"
        assert parsed["resource_type"] == "Microsoft.Compute/disks"
        assert parsed["resource_name"] == "disk-01"


# ── TestBuildResourceContext ────────────────────────────────────────────────────


class TestBuildResourceContext:
    """Tests for Resource Context building."""

    def _create_mock_opportunity(
        self,
        resource_id: str = "",
        resource_name: str = "",
        service: str = "",
        region: str = "",
        environment: str = "",
        owner_team: str = "",
        sku_name: str = "",
    ) -> MagicMock:
        """Create a mock OptimizationOpportunity."""
        opp = MagicMock()
        opp.resource_id = resource_id
        opp.resource_name = resource_name
        opp.service = service
        opp.region = region
        opp.environment = environment
        opp.owner_team = owner_team
        opp.sku_name = sku_name
        opp.decision_evidence = None
        return opp

    def test_enrich_with_parsed_fields(self):
        """Test enrichment with parsed ARM fields."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
            resource_name="",  # Empty - will be parsed from resource_id
        )

        ctx = build_resource_context(opp)

        assert ctx.resource_type == "Microsoft.Compute/virtualMachines"
        assert ctx.resource_group == "rg"
        assert ctx.resource_name == "vm-01"
        assert ctx.portal_url is not None
        assert "portal.azure.com/#resource" in ctx.portal_url

    def test_owner_null_when_no_inventory(self):
        """Test that owner is None when no inventory data."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
        )

        ctx = build_resource_context(opp)

        assert ctx.owner is None

    def test_portal_url_for_subscription_level(self):
        """Test that portal_url is None for subscription-level resources."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx",
        )

        ctx = build_resource_context(opp)

        assert ctx.portal_url is None

    def test_portal_url_for_resource_level(self):
        """Test that portal_url is generated for resource-level resources."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
        )

        ctx = build_resource_context(opp)

        assert ctx.portal_url is not None
        assert "https://portal.azure.com/#resource" in ctx.portal_url

    def test_resource_name_priority_existing_valid(self):
        """Test that existing valid resource_name takes priority."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
            resource_name="my-custom-vm",  # Valid existing name
        )

        ctx = build_resource_context(opp)

        assert ctx.resource_name == "my-custom-vm"

    def test_resource_name_fallback_to_parsed(self):
        """Test fallback to parsed resource_name when existing is subscription_id."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
            resource_name="xxx",  # Same as subscription_id - should fallback
        )

        ctx = build_resource_context(opp)

        assert ctx.resource_name == "vm-01"  # Should use parsed

    def test_tags_summary_null_when_no_inventory(self):
        """Test that tags_summary is None when no inventory."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
        )

        ctx = build_resource_context(opp)

        assert ctx.tags_summary is None

    def test_child_resource_parsing(self):
        """Test parsing child resources correctly."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Sql/servers/sql-01/databases/db-01",
        )

        ctx = build_resource_context(opp)

        assert ctx.resource_type == "Microsoft.Sql/servers/databases"
        assert ctx.resource_name == "db-01"
        assert ctx.resource_group == "rg"
        assert ctx.portal_url is not None

    def test_granularity_tier_subscription(self):
        """Test granularity tier for subscription-level."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx",
        )

        ctx = build_resource_context(opp)

        assert ctx.granularity_tier == "subscription"

    def test_granularity_tier_resource(self):
        """Test granularity tier for resource-level."""
        opp = self._create_mock_opportunity(
            resource_id="/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-01",
        )

        ctx = build_resource_context(opp)

        assert ctx.granularity_tier == "resource"
