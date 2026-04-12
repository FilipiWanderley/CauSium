from __future__ import annotations

from app.domains.cloud_accounts.models import CloudProvider
from app.domains.connectors.aws.client import AwsConnectorClient
from app.domains.connectors.azure.client import AzureConnectorClient


def get_connector_for_account(account, creds):
    if account.provider == CloudProvider.AZURE:
        return AzureConnectorClient.from_account(account, creds)
    if account.provider == CloudProvider.AWS:
        return AwsConnectorClient.from_account(account, creds)
    raise ValueError(f"Unsupported provider '{account.provider.value}'")
