from __future__ import annotations
import csv
import io
import json

from datetime import date, datetime, timezone

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.connectors.base import BaseConnector, CanonicalCarbonRecord, CanonicalCostRecord, CanonicalEventRecord

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

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        *,
        storage_account_url: str | None = None,
        cost_export_container: str | None = None,
        cost_export_prefix: str | None = None,
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.storage_account_url = storage_account_url
        self.cost_export_container = cost_export_container
        self.cost_export_prefix = cost_export_prefix or ""
        self._credential = None
        self._last_blob_checkpoints: list[dict[str, str]] = []

    @classmethod
    def from_account(cls, account, creds) -> "AzureConnectorClient":
        settings = get_settings()
        if creds:
            return cls(
                tenant_id=creds.tenant_id,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                storage_account_url=creds.storage_account_url,
                cost_export_container=creds.cost_export_container,
                cost_export_prefix=creds.cost_export_prefix,
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

    async def validate_cost_management_scope(self, subscription_id: str) -> None:
        """Verify the SP has at minimum Cost Management Reader on the given subscription.

        Raises PermissionError if the required role assignment is absent.
        The check is best-effort: if the ARM API is unreachable we log a warning
        and continue rather than blocking account creation.
        """
        try:
            from azure.mgmt.authorization import AuthorizationManagementClient

            cred = self._get_credential()
            auth_client = AuthorizationManagementClient(cred, subscription_id)
            scope = f"/subscriptions/{subscription_id}"
            assignments = list(auth_client.role_assignments.list_for_scope(scope))

            COST_READER_ID = "72fafb9e-0641-4937-9268-a91bfd8191a3"
            COST_CONTRIBUTOR_ID = "434105ed-43f6-45c7-a02f-909b2ba83430"
            OWNER_ID = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
            CONTRIBUTOR_ID = "b24988ac-6180-42a0-ab88-20f7382dd24c"
            READER_ID = "acdd72a7-3385-48ef-bd42-f606fba81ae7"

            allowed_role_ids = {
                COST_READER_ID,
                COST_CONTRIBUTOR_ID,
                OWNER_ID,
                CONTRIBUTOR_ID,
                READER_ID,
            }

            has_permission = any(
                a.role_definition_id and a.role_definition_id.split("/")[-1] in allowed_role_ids
                for a in assignments
            )

            if not has_permission:
                raise PermissionError(
                    "The service principal lacks Cost Management Reader (or higher) "
                    f"on subscription '{subscription_id}'. "
                    "Grant the role before adding this account."
                )
            log.info("azure.scope_validation.ok", subscription_id=subscription_id)
        except PermissionError:
            raise
        except Exception as exc:
            log.warning(
                "azure.scope_validation.skipped",
                subscription_id=subscription_id,
                reason=str(exc),
            )

    async def fetch_costs(
        self,
        subscription_id: str,
        start: date,
        end: date,
        *,
        checkpoint_keys: set[str] | None = None,
    ) -> list[CanonicalCostRecord]:
        self._last_blob_checkpoints = []
        blob_records, blob_checkpoints = await self._fetch_costs_from_blob_exports(
            subscription_id,
            start,
            end,
            checkpoint_keys=checkpoint_keys,
        )
        self._last_blob_checkpoints = blob_checkpoints
        if blob_records:
            log.info(
                "azure.fetch_costs.blob.done",
                subscription=subscription_id,
                records=len(blob_records),
                container=self.cost_export_container,
            )
            return blob_records

        return await self._fetch_costs_from_cost_management_api(subscription_id, start, end)

    def consume_last_blob_checkpoints(self) -> list[dict[str, str]]:
        items = self._last_blob_checkpoints
        self._last_blob_checkpoints = []
        return items

    async def _fetch_costs_from_cost_management_api(
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

    async def _fetch_costs_from_blob_exports(
        self,
        subscription_id: str,
        start: date,
        end: date,
        *,
        checkpoint_keys: set[str] | None = None,
    ) -> tuple[list[CanonicalCostRecord], list[dict[str, str]]]:
        if not self.storage_account_url or not self.cost_export_container:
            return [], []

        from azure.storage.blob.aio import BlobServiceClient

        cred = self._get_credential()
        records: list[CanonicalCostRecord] = []
        consumed_checkpoints: list[dict[str, str]] = []
        seen_checkpoints: set[str] = set()

        try:
            blob_service = BlobServiceClient(account_url=self.storage_account_url, credential=cred)
            container = blob_service.get_container_client(self.cost_export_container)

            async for blob in container.list_blobs(name_starts_with=self.cost_export_prefix or None):
                blob_name = str(getattr(blob, "name", ""))
                if not blob_name.lower().endswith(".csv"):
                    continue

                blob_etag = str(getattr(blob, "etag", "") or "")
                checkpoint_key = self._build_blob_checkpoint_key(blob_name, blob_etag)
                if checkpoint_keys and checkpoint_key in checkpoint_keys:
                    continue
                if checkpoint_key in seen_checkpoints:
                    continue

                try:
                    downloader = await container.download_blob(blob_name)
                    payload = await downloader.readall()
                    text = payload.decode("utf-8-sig", errors="replace")
                    records.extend(self._parse_blob_cost_csv(text, subscription_id, start, end))
                    consumed_checkpoints.append(
                        {
                            "checkpoint_key": checkpoint_key,
                            "blob_name": blob_name,
                            "blob_etag": blob_etag,
                        }
                    )
                    seen_checkpoints.add(checkpoint_key)
                except Exception as exc:
                    log.warning(
                        "azure.fetch_costs.blob_item.failed",
                        subscription=subscription_id,
                        blob_name=blob_name,
                        reason=str(exc),
                    )
                    continue

        except Exception as exc:
            log.warning(
                "azure.fetch_costs.blob.failed",
                subscription=subscription_id,
                container=self.cost_export_container,
                reason=str(exc),
            )
            return [], []

        return records, consumed_checkpoints

    @staticmethod
    def _build_blob_checkpoint_key(blob_name: str, blob_etag: str) -> str:
        return f"{blob_name}::{blob_etag or '-'}"

    @staticmethod
    def _parse_blob_cost_csv(
        raw_csv: str,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCostRecord]:
        reader = csv.DictReader(io.StringIO(raw_csv))
        rows: list[CanonicalCostRecord] = []
        for row in reader:
            normalized = AzureConnectorClient._normalize_blob_cost_row(row, subscription_id, start, end)
            if normalized:
                rows.append(normalized)
        return rows

    @staticmethod
    def _normalize_blob_cost_row(
        row: dict,
        fallback_subscription_id: str,
        start: date,
        end: date,
    ) -> CanonicalCostRecord | None:
        normalized = {str(k).strip().lower(): ("" if v is None else str(v).strip()) for k, v in row.items()}

        usage_date_raw = normalized.get("date") or normalized.get("usagedate") or normalized.get("usage_date")
        if not usage_date_raw:
            return None

        usage_date = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                usage_date = datetime.strptime(usage_date_raw, fmt).date()
                break
            except ValueError:
                continue
        if usage_date is None:
            return None
        if usage_date < start or usage_date > end:
            return None

        record_subscription_id = (
            normalized.get("subscriptionid")
            or normalized.get("subscription_id")
            or fallback_subscription_id
        )
        if record_subscription_id and record_subscription_id != fallback_subscription_id:
            return None

        tags_raw = normalized.get("tags", "")
        tags = {}
        if tags_raw:
            try:
                parsed = json.loads(tags_raw)
                if isinstance(parsed, dict):
                    tags = {str(k): str(v) for k, v in parsed.items()}
            except Exception:
                tags = {}

        def _float_value(*keys: str) -> float:
            for key in keys:
                value = normalized.get(key)
                if not value:
                    continue
                try:
                    return float(value)
                except ValueError:
                    continue
            return 0.0

        resource_group = normalized.get("resourcegroup") or normalized.get("resource_group")
        resource_name = normalized.get("resourcename") or normalized.get("resource_name") or resource_group or ""

        return CanonicalCostRecord(
            date=usage_date,
            provider="azure",
            subscription_id=record_subscription_id or fallback_subscription_id,
            service=normalized.get("servicename") or normalized.get("service") or "unknown",
            resource_id=normalized.get("resourceid") or normalized.get("resource_id") or "",
            resource_name=resource_name,
            region=normalized.get("resourcelocation") or normalized.get("region") or "unknown",
            environment=_infer_environment(tags),
            owner_team=_infer_owner_team(tags),
            cost_usd=_float_value("pretaxcost", "cost", "costusd", "cost_usd"),
            usage_quantity=_float_value("usagequantity", "quantity", "usage_quantity"),
            usage_unit=normalized.get("unitofmeasure") or normalized.get("usageunit") or "",
            currency=normalized.get("currency") or "USD",
            tags=tags,
        )

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

    async def fetch_carbon_emissions(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCarbonRecord]:
        settings = get_settings()
        if not settings.azure_carbon_api_url:
            log.info("azure.fetch_carbon.skipped", reason="AZURE_CARBON_API_URL not configured")
            return []

        cred = self._get_credential()
        token = cred.get_token("https://management.azure.com/.default")

        payload = {
            "subscriptionId": subscription_id,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    settings.azure_carbon_api_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token.token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            log.warning("azure.fetch_carbon.failed", subscription=subscription_id, reason=str(exc))
            return []

        items = data.get("value") if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []

        records: list[CanonicalCarbonRecord] = []
        for item in items:
            normalized = self._normalize_carbon_item(item, subscription_id)
            if normalized:
                records.append(normalized)

        log.info("azure.fetch_carbon.done", subscription=subscription_id, records=len(records))
        return records

    @staticmethod
    def _normalize_carbon_item(item: dict, fallback_subscription_id: str) -> CanonicalCarbonRecord | None:
        if not isinstance(item, dict):
            return None

        year_month = (
            item.get("yearMonth")
            or item.get("month")
            or item.get("billingMonth")
            or ""
        )
        year_month = str(year_month)
        if len(year_month) == 6 and year_month.isdigit():
            year_month = f"{year_month[:4]}-{year_month[4:6]}"
        if len(year_month) != 7:
            return None

        raw_kg = item.get("kgCO2e") or item.get("kg_co2e") or item.get("emissionsKg") or 0
        try:
            kg = float(raw_kg)
        except (TypeError, ValueError):
            return None

        return CanonicalCarbonRecord(
            year_month=year_month,
            provider="azure",
            subscription_id=str(item.get("subscriptionId") or fallback_subscription_id),
            service=str(item.get("serviceName") or item.get("service") or "unknown"),
            resource_group=str(item.get("resourceGroupName") or item.get("resourceGroup") or "unknown"),
            kg_co2e=kg,
        )


# Import mock at the bottom to avoid circular import
from app.domains.connectors.azure.mock import AzureMockClient  # noqa: E402
