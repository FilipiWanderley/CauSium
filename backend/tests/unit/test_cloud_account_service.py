"""
Unit tests for cloud_accounts service subscription backfill with Azure names.

Tests that subscription_name and display_name are populated from Azure API
during the backfill process.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domains.cloud_accounts.models import (
    CloudAccount,
    CloudAccountSubscription,
    CloudProvider,
    SubscriptionStatus,
)


class MockAzureCredentials:
    """Mock Azure credentials for testing."""

    def __init__(self):
        self.tenant_id = "test-tenant-id"
        self.client_id = "test-client-id"
        self.client_secret = "test-client-secret"
        self.subscription_id = "test-subscription-id"


class TestFetchAzureSubscriptionNames:
    """Tests for _fetch_azure_subscription_names method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_non_azure_accounts(self):
        """Non-Azure accounts should return empty dict."""
        from app.domains.cloud_accounts.service import CloudAccountService

        service = CloudAccountService(db=MagicMock())

        aws_account = MagicMock(spec=CloudAccount)
        aws_account.provider = CloudProvider.AWS
        aws_account.id = uuid4()

        result = await service._fetch_azure_subscription_names([aws_account])

        assert result == {}

    @pytest.mark.asyncio
    async def test_fetches_names_for_azure_accounts(self):
        """Azure accounts should have their subscription names fetched."""
        from app.domains.cloud_accounts.service import CloudAccountService

        service = CloudAccountService(db=MagicMock())

        azure_account = MagicMock(spec=CloudAccount)
        azure_account.provider = CloudProvider.AZURE
        azure_account.id = uuid4()

        mock_creds = MockAzureCredentials()
        service.get_azure_credentials = AsyncMock(return_value=mock_creds)

        expected_names = [
            ("sub-123", "Production Subscription"),
            ("sub-456", "Development Subscription"),
        ]

        with patch(
            "app.domains.connectors.azure.client.AzureConnectorClient"
        ) as MockClient:
            mock_client = AsyncMock()
            mock_client.list_accessible_subscriptions_with_names.return_value = expected_names
            MockClient.return_value = mock_client

            result = await service._fetch_azure_subscription_names([azure_account])

        assert str(azure_account.id) in result
        assert result[str(azure_account.id)]["sub-123"] == "Production Subscription"

    @pytest.mark.asyncio
    async def test_handles_azure_api_failure_gracefully(self):
        """Azure API failure should not break the method."""
        from app.domains.cloud_accounts.service import CloudAccountService

        service = CloudAccountService(db=MagicMock())

        azure_account = MagicMock(spec=CloudAccount)
        azure_account.provider = CloudProvider.AZURE
        azure_account.id = uuid4()

        mock_creds = MockAzureCredentials()
        service.get_azure_credentials = AsyncMock(return_value=mock_creds)

        with patch(
            "app.domains.connectors.azure.client.AzureConnectorClient"
        ) as MockClient:
            mock_client = AsyncMock()
            mock_client.list_accessible_subscriptions_with_names.side_effect = Exception(
                "Azure API Error"
            )
            MockClient.return_value = mock_client

            # Should not raise, should return empty
            result = await service._fetch_azure_subscription_names([azure_account])

        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_missing_credentials(self):
        """Missing credentials should be skipped."""
        from app.domains.cloud_accounts.service import CloudAccountService

        service = CloudAccountService(db=MagicMock())

        azure_account = MagicMock(spec=CloudAccount)
        azure_account.provider = CloudProvider.AZURE
        azure_account.id = uuid4()

        service.get_azure_credentials = AsyncMock(return_value=None)

        result = await service._fetch_azure_subscription_names([azure_account])

        assert result == {}


class TestBackfillPopulatesAzureSubscriptionNames:
    """Tests that backfill correctly populates subscription names."""

    @pytest.mark.asyncio
    async def test_new_subscription_receives_name_from_azure_api(self):
        """New Azure subscriptions should get their name from Azure API."""
        from app.domains.cloud_accounts.service import CloudAccountService

        org_id = uuid4()
        account_id = uuid4()

        # Mock DB session
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        service = CloudAccountService(db=mock_db)

        # Mock discovered subscriptions (from cost_facts)
        discovered = [
            {
                "org_id": str(org_id),
                "cloud_account_id": str(account_id),
                "provider": "azure",
                "cloud_tenant_id": "tenant-123",
                "subscription_id": "sub-abc-123",
            }
        ]

        with patch.object(
            service, "discover_subscriptions_from_cost_facts", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = {
                "subscriptions": discovered,
                "skipped_subscriptions": [],
            }

            # Mock existing subscriptions (none found)
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            # Mock accounts list
            azure_account = MagicMock(spec=CloudAccount)
            azure_account.id = account_id
            azure_account.org_id = org_id
            azure_account.provider = CloudProvider.AZURE
            azure_account.tenant_id = "tenant-123"

            with patch.object(service, "list_accounts", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = ([azure_account], 1)

                # Mock Azure API returning subscription name
                service.get_azure_credentials = AsyncMock(
                    return_value=MockAzureCredentials()
                )

                with patch(
                    "app.domains.connectors.azure.client.AzureConnectorClient"
                ) as MockClient:
                    mock_client = AsyncMock()
                    mock_client.list_accessible_subscriptions_with_names.return_value = [
                        ("sub-abc-123", "Production Azure Subscription"),
                    ]
                    MockClient.return_value = mock_client

                    # Mock flush
                    mock_db.flush = AsyncMock()

                    # Execute backfill
                    result = await service.backfill_subscriptions_from_cost_facts(
                        org_id=org_id, dry_run=False
                    )

        # Verify subscription was created with name
        assert result["inserted_count"] == 1
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_existing_null_name_is_backfilled(self):
        """Existing subscriptions with NULL name should be updated."""
        from app.domains.cloud_accounts.service import CloudAccountService

        org_id = uuid4()
        account_id = uuid4()
        sub_id = "sub-existing-123"

        mock_db = AsyncMock()
        service = CloudAccountService(db=mock_db)

        # Mock existing subscription with NULL name
        existing_sub = MagicMock(spec=CloudAccountSubscription)
        existing_sub.id = uuid4()
        existing_sub.cloud_account_id = account_id
        existing_sub.provider = CloudProvider.AZURE
        existing_sub.subscription_id = sub_id
        existing_sub.subscription_name = None
        existing_sub.display_name = None
        existing_sub.status = SubscriptionStatus.DISCOVERED
        existing_sub.last_seen_at = None

        discovered = [
            {
                "org_id": str(org_id),
                "cloud_account_id": str(account_id),
                "provider": "azure",
                "cloud_tenant_id": "tenant-123",
                "subscription_id": sub_id,
            }
        ]

        with patch.object(
            service, "discover_subscriptions_from_cost_facts", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = {
                "subscriptions": discovered,
                "skipped_subscriptions": [],
            }

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [existing_sub]
            mock_db.execute = AsyncMock(return_value=mock_result)

            azure_account = MagicMock(spec=CloudAccount)
            azure_account.id = account_id
            azure_account.org_id = org_id
            azure_account.provider = CloudProvider.AZURE
            azure_account.tenant_id = "tenant-123"

            with patch.object(service, "list_accounts", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = ([azure_account], 1)

                service.get_azure_credentials = AsyncMock(
                    return_value=MockAzureCredentials()
                )

                with patch(
                    "app.domains.connectors.azure.client.AzureConnectorClient"
                ) as MockClient:
                    mock_client = AsyncMock()
                    mock_client.list_accessible_subscriptions_with_names.return_value = [
                        (sub_id, "Existing Subscription Name"),
                    ]
                    MockClient.return_value = mock_client

                    mock_db.flush = AsyncMock()

                    result = await service.backfill_subscriptions_from_cost_facts(
                        org_id=org_id, dry_run=False
                    )

        # Verify subscription was updated
        assert result["updated_count"] == 1
        assert existing_sub.subscription_name == "Existing Subscription Name"
        assert existing_sub.display_name == "Existing Subscription Name"

    @pytest.mark.asyncio
    async def test_existing_name_is_not_overwritten(self):
        """Existing non-NULL names should NOT be overwritten."""
        from app.domains.cloud_accounts.service import CloudAccountService

        org_id = uuid4()
        account_id = uuid4()
        sub_id = "sub-existing-456"

        mock_db = AsyncMock()
        service = CloudAccountService(db=mock_db)

        # Mock existing subscription with existing name
        existing_sub = MagicMock(spec=CloudAccountSubscription)
        existing_sub.id = uuid4()
        existing_sub.cloud_account_id = account_id
        existing_sub.provider = CloudProvider.AZURE
        existing_sub.subscription_id = sub_id
        existing_sub.subscription_name = "Original Name"  # Already has name
        existing_sub.display_name = "Original Name"
        existing_sub.status = SubscriptionStatus.ACTIVE
        existing_sub.last_seen_at = None

        discovered = [
            {
                "org_id": str(org_id),
                "cloud_account_id": str(account_id),
                "provider": "azure",
                "cloud_tenant_id": "tenant-123",
                "subscription_id": sub_id,
            }
        ]

        with patch.object(
            service, "discover_subscriptions_from_cost_facts", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = {
                "subscriptions": discovered,
                "skipped_subscriptions": [],
            }

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [existing_sub]
            mock_db.execute = AsyncMock(return_value=mock_result)

            azure_account = MagicMock(spec=CloudAccount)
            azure_account.id = account_id
            azure_account.org_id = org_id
            azure_account.provider = CloudProvider.AZURE
            azure_account.tenant_id = "tenant-123"

            with patch.object(service, "list_accounts", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = ([azure_account], 1)

                service.get_azure_credentials = AsyncMock(
                    return_value=MockAzureCredentials()
                )

                with patch(
                    "app.domains.connectors.azure.client.AzureConnectorClient"
                ) as MockClient:
                    mock_client = AsyncMock()
                    mock_client.list_accessible_subscriptions_with_names.return_value = [
                        (sub_id, "Azure API Name"),
                    ]
                    MockClient.return_value = mock_client

                    mock_db.flush = AsyncMock()

                    result = await service.backfill_subscriptions_from_cost_facts(
                        org_id=org_id, dry_run=False
                    )

        # Verify subscription was NOT modified (original name preserved)
        assert result["updated_count"] == 1
        assert existing_sub.subscription_name == "Original Name"
        assert existing_sub.display_name == "Original Name"

    @pytest.mark.asyncio
    async def test_azure_api_failure_does_not_break_backfill(self):
        """Azure API failure should not break the backfill process."""
        from app.domains.cloud_accounts.service import CloudAccountService

        org_id = uuid4()
        account_id = uuid4()
        sub_id = "sub-fail-789"

        mock_db = AsyncMock()
        service = CloudAccountService(db=mock_db)

        discovered = [
            {
                "org_id": str(org_id),
                "cloud_account_id": str(account_id),
                "provider": "azure",
                "cloud_tenant_id": "tenant-123",
                "subscription_id": sub_id,
            }
        ]

        with patch.object(
            service, "discover_subscriptions_from_cost_facts", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = {
                "subscriptions": discovered,
                "skipped_subscriptions": [],
            }

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            azure_account = MagicMock(spec=CloudAccount)
            azure_account.id = account_id
            azure_account.org_id = org_id
            azure_account.provider = CloudProvider.AZURE
            azure_account.tenant_id = "tenant-123"

            with patch.object(service, "list_accounts", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = ([azure_account], 1)

                service.get_azure_credentials = AsyncMock(
                    return_value=MockAzureCredentials()
                )

                # Simulate Azure API failure
                with patch(
                    "app.domains.connectors.azure.client.AzureConnectorClient"
                ) as MockClient:
                    mock_client = AsyncMock()
                    mock_client.list_accessible_subscriptions_with_names.side_effect = (
                        Exception("Azure API Error")
                    )
                    MockClient.return_value = mock_client

                    mock_db.flush = AsyncMock()

                    # Should not raise
                    result = await service.backfill_subscriptions_from_cost_facts(
                        org_id=org_id, dry_run=False
                    )

        # Backfill should complete with NULL name (graceful degradation)
        assert result["inserted_count"] == 1

    @pytest.mark.asyncio
    async def test_non_azure_providers_unchanged(self):
        """Non-Azure providers should work as before (no Azure API calls)."""
        from app.domains.cloud_accounts.service import CloudAccountService

        org_id = uuid4()
        account_id = uuid4()
        sub_id = "aws-account-123"

        mock_db = AsyncMock()
        service = CloudAccountService(db=mock_db)

        discovered = [
            {
                "org_id": str(org_id),
                "cloud_account_id": str(account_id),
                "provider": "aws",
                "cloud_tenant_id": None,
                "subscription_id": sub_id,
            }
        ]

        with patch.object(
            service, "discover_subscriptions_from_cost_facts", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = {
                "subscriptions": discovered,
                "skipped_subscriptions": [],
            }

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            aws_account = MagicMock(spec=CloudAccount)
            aws_account.id = account_id
            aws_account.org_id = org_id
            aws_account.provider = CloudProvider.AWS
            aws_account.tenant_id = None

            with patch.object(service, "list_accounts", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = ([aws_account], 1)

                # Should not call get_azure_credentials for AWS
                service.get_azure_credentials = AsyncMock()

                mock_db.flush = AsyncMock()

                result = await service.backfill_subscriptions_from_cost_facts(
                    org_id=org_id, dry_run=False
                )

        # Subscription created but with NULL name (AWS doesn't use Azure API)
        assert result["inserted_count"] == 1
        service.get_azure_credentials.assert_not_called()
