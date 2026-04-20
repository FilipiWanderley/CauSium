from __future__ import annotations

from app.domains.cloud_accounts.models import CloudProvider
from app.domains.connectors.aws.client import AwsConnectorClient
from app.domains.connectors.azure.client import AzureConnectorClient
from app.domains.connectors.gcp.client import GcpConnectorClient


def _normalize_provider(provider: object) -> CloudProvider | None:
    if isinstance(provider, CloudProvider):
        return provider
    if isinstance(provider, str):
        raw = provider.strip().lower()
        for candidate in CloudProvider:
            if raw == candidate.value or raw == candidate.name.lower():
                return candidate
    return None


def get_connector_for_account(account, creds):
    provider = _normalize_provider(getattr(account, "provider", None))
    if provider == CloudProvider.AZURE:
        return AzureConnectorClient.from_account(account, creds)
    if provider == CloudProvider.AWS:
        return AwsConnectorClient.from_account(account, creds)
    if provider == CloudProvider.GCP:
        return GcpConnectorClient.from_account(account, creds)
    raise ValueError(f"Unsupported provider '{getattr(account, 'provider', None)}'")
