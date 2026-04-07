from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.connectors.base import BaseConnector, CanonicalCostRecord, CanonicalEventRecord

log = get_logger(__name__)


def _parse_tags(tags: dict | None) -> dict[str, str]:
    if not tags:
        return {}
    return {str(k): str(v) for k, v in tags.items()}


def _infer_environment(tags: dict[str, str]) -> str:
    for key in ("env", "environment", "Environment", "Env"):
        val = tags.get(key, "").lower()
        if val in ("prod", "production"):
            return "production"
        if val in ("staging", "stage"):
            return "staging"
        if val in ("dev", "development"):
            return "development"
    return "unknown"


def _infer_owner_team(tags: dict[str, str]) -> str:
    for key in ("team", "owner", "squad", "Team", "Owner", "Squad"):
        if val := tags.get(key):
            return val
    return "untagged"


class AzureConnectorClient(BaseConnector):
    """Real Azure connector using Service Principal credentials."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._credential = None

    @classmethod
    def from_account(cls, account, creds) -> "AzureConnectorClient":
        settings = get_settings()
        if creds:
            return cls(
                tenant_id=creds.tenant_id,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
            )
        if settings.azure_credentials_available:
            return cls(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
        log.warning("azure.connector.no_credentials — falling back to mock", account_id=str(account.id))
        return AzureMockClient()  # type: ignore[return-value]

    def _get_credential(self):
        if self._credential is None:
            from azure.identity import ClientSecretCredential

            self._credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
        return self._credential

    async def validate_connection(self) -> None:
        from azure.mgmt.subscription import SubscriptionClient

        cred = self._get_credential()
        client = SubscriptionClient(cred)
        subs = list(client.subscriptions.list())
        log.info("azure.validate_connection.ok", subscriptions=len(subs))

    async def fetch_costs(
        self, subscription_id: str, start: date, end: date
    ) -> list[CanonicalCostRecord]:
        from azure.mgmt.costmanagement import CostManagementClient
        from azure.mgmt.costmanagement.models import (
            ExportType,
            GranularityType,
            QueryDataset,
            QueryDefinition,
            QueryTimePeriod,
        )

        cred = self._get_credential()
        client = CostManagementClient(cred)
        scope = f"/subscriptions/{subscription_id}"

        query = QueryDefinition(
            type=ExportType.ACTUAL_COST,
            timeframe="Custom",
            time_period=QueryTimePeriod(
                from_property=datetime(start.year, start.month, start.day, tzinfo=timezone.utc),
                to=datetime(end.year, end.month, end.day, tzinfo=timezone.utc),
            ),
            dataset=QueryDataset(
                granularity=GranularityType.DAILY,
                grouping=[
                    {"type": "Dimension", "name": "ServiceName"},
                    {"type": "Dimension", "name": "ResourceId"},
                    {"type": "Dimension", "name": "ResourceGroupName"},
                    {"type": "Dimension", "name": "ResourceLocation"},
                ],
            ),
        )

        result = client.query.usage(scope=scope, parameters=query)
        columns = [col.name for col in result.columns]
        records: list[CanonicalCostRecord] = []

        for row in result.rows:
            row_dict = dict(zip(columns, row))
            tags = _parse_tags(row_dict.get("Tags"))
            records.append(
                CanonicalCostRecord(
                    date=start,
                    provider="azure",
                    subscription_id=subscription_id,
                    service=str(row_dict.get("ServiceName", "unknown")),
                    resource_id=str(row_dict.get("ResourceId", "")),
                    resource_name=str(row_dict.get("ResourceGroupName", "")),
                    region=str(row_dict.get("ResourceLocation", "unknown")),
                    environment=_infer_environment(tags),
                    owner_team=_infer_owner_team(tags),
                    cost_usd=float(row_dict.get("PreTaxCost", row_dict.get("Cost", 0))),
                    usage_quantity=float(row_dict.get("UsageQuantity", 0)),
                    usage_unit=str(row_dict.get("UnitOfMeasure", "")),
                    currency=str(row_dict.get("Currency", "USD")),
                    tags=tags,
                )
            )

        log.info("azure.fetch_costs.done", subscription=subscription_id, records=len(records))
        return records

    async def fetch_events(
        self, subscription_id: str, start: date, end: date
    ) -> list[CanonicalEventRecord]:
        from azure.mgmt.monitor import MonitorManagementClient

        cred = self._get_credential()
        client = MonitorManagementClient(cred, subscription_id)

        filter_str = (
            f"eventTimestamp ge '{start.isoformat()}T00:00:00Z' "
            f"and eventTimestamp le '{end.isoformat()}T23:59:59Z'"
        )
        events = list(
            client.activity_logs.list(
                filter=filter_str,
                select="eventTimestamp,operationName,resourceId,resourceGroupName,resourceProviderName,status,caller,correlationId,level,description",
            )
        )

        records: list[CanonicalEventRecord] = []
        for ev in events:
            ts = ev.event_timestamp or datetime.now(timezone.utc)
            records.append(
                CanonicalEventRecord(
                    timestamp=ts,
                    provider="azure",
                    subscription_id=subscription_id,
                    event_type=str(ev.operation_name.value if ev.operation_name else "unknown"),
                    resource_id=str(ev.resource_id or ""),
                    resource_name=str(ev.resource_group_name or ""),
                    region="azure",
                    severity=str(ev.level.value if ev.level else "informational"),
                    description=str(ev.description or ""),
                    caller=str(ev.caller or ""),
                    correlation_id=str(ev.correlation_id or ""),
                    raw_data="",
                )
            )

        log.info("azure.fetch_events.done", subscription=subscription_id, records=len(records))
        return records


# Import mock at the bottom to avoid circular import
from app.domains.connectors.azure.mock import AzureMockClient  # noqa: E402
