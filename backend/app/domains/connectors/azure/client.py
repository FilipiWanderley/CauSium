from __future__ import annotations
import asyncio
import csv
import io
import itertools
import json
import os

from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.connectors.base import (
    BaseConnector,
    CanonicalCarbonRecord,
    CanonicalCostRecord,
    CanonicalEventRecord,
    CanonicalRecommendationRecord,
    CanonicalResourceRecord,
    CanonicalUsageRecord,
)

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
        cost_export_format: str = "auto",
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.storage_account_url = storage_account_url
        self.cost_export_container = cost_export_container
        self.cost_export_prefix = cost_export_prefix or ""
        self.cost_export_format = cost_export_format
        self._credential = None
        self._last_blob_checkpoints: list[dict[str, str]] = []
        self._last_scope_warnings: list[str] = []

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
                cost_export_format=creds.cost_export_format,
            )
        if settings.azure_credentials_available:
            return cls(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
        app_env = os.getenv("APP_ENV", settings.app_env).strip().lower()
        environment = os.getenv("ENVIRONMENT", "").strip().lower()
        is_production = app_env == "production" or environment == "production"
        if is_production:
            raise ValueError(
                "Azure credentials are required in production. "
                "Refusing to fallback to AzureMockClient when APP_ENV/ENVIRONMENT is production."
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
        subs = await asyncio.to_thread(lambda: list(client.subscriptions.list()))
        log.info("azure.validate_connection.ok", subscriptions=len(subs))

    async def list_accessible_subscriptions(self) -> list[str]:
        """Return all subscription IDs accessible to the Service Principal."""
        from azure.mgmt.subscription import SubscriptionClient

        cred = self._get_credential()
        client = SubscriptionClient(cred)
        subs = await asyncio.to_thread(lambda: list(client.subscriptions.list()))
        ids = [s.subscription_id for s in subs if s.subscription_id]
        log.info("azure.list_accessible_subscriptions", count=len(ids), subscription_ids=ids)
        return ids

    async def list_accessible_subscriptions_with_names(self) -> list[tuple[str, str]]:
        """Return (subscription_id, display_name) pairs for all accessible subscriptions."""
        from azure.mgmt.subscription import SubscriptionClient

        cred = self._get_credential()
        client = SubscriptionClient(cred)
        subs = await asyncio.to_thread(lambda: list(client.subscriptions.list()))
        return [
            (s.subscription_id, s.display_name or s.subscription_id)
            for s in subs
            if s.subscription_id
        ]

    async def validate_cost_management_scope(self, subscription_id: str) -> None:
        """Verify the SP has at minimum Cost Management Reader on the given subscription.

        Raises PermissionError if the required role assignment is absent.
        The check is best-effort: if the ARM API is unreachable we log a warning
        and continue rather than blocking account creation.
        """
        self._last_scope_warnings = []
        try:
            from azure.mgmt.authorization import AuthorizationManagementClient

            cred = self._get_credential()
            auth_client = AuthorizationManagementClient(cred, subscription_id)
            scope = f"/subscriptions/{subscription_id}"
            assignments = await asyncio.to_thread(
                lambda: list(auth_client.role_assignments.list_for_scope(scope))
            )

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
            elevated_role_ids = {OWNER_ID, CONTRIBUTOR_ID}

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

            matched_role_ids = {
                a.role_definition_id.split("/")[-1]
                for a in assignments
                if a.role_definition_id
            }
            if matched_role_ids & elevated_role_ids:
                warning_msg = (
                    "Detected elevated Azure role assignment (Owner/Contributor). "
                    "For least privilege in CauSium read-only mode, prefer Reader + "
                    "Cost Management Reader."
                )
                self._last_scope_warnings = [warning_msg]
                log.warning(
                    "azure.scope_validation.excessive_permissions",
                    subscription_id=subscription_id,
                    recommendation="Reader + Cost Management Reader",
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

    def get_last_scope_warnings(self) -> list[str]:
        return list(self._last_scope_warnings)

    async def validate_storage_access(self) -> None:
        """Validate data-plane access to the configured Blob container."""
        if not self.storage_account_url or not self.cost_export_container:
            return

        try:
            from azure.storage.blob.aio import BlobServiceClient

            cred = self._get_credential()
            blob_service = BlobServiceClient(account_url=self.storage_account_url, credential=cred)
            container = blob_service.get_container_client(self.cost_export_container)
            await container.get_container_properties()
            await blob_service.close()
            log.info(
                "azure.storage_validation.ok",
                storage_account_url=self.storage_account_url,
                container=self.cost_export_container,
            )
        except Exception as exc:
            raise PermissionError(
                "The service principal cannot access the configured Azure Blob container. "
                "Ensure 'Storage Blob Data Reader' (or higher) is granted."
            ) from exc

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

        records: list[CanonicalCostRecord] = []

        def _to_float(value: object) -> float:
            if value is None:
                return 0.0
            try:
                return float(value)
            except (TypeError, ValueError):
                raw = str(value).strip()
                cleaned = "".join(ch for ch in raw if ch.isdigit() or ch in ",.-")
                if not cleaned:
                    return 0.0
                if "," in cleaned and "." in cleaned:
                    if cleaned.rfind(",") > cleaned.rfind("."):
                        cleaned = cleaned.replace(".", "").replace(",", ".")
                    else:
                        cleaned = cleaned.replace(",", "")
                elif "," in cleaned:
                    cleaned = cleaned.replace(",", ".")
                try:
                    return float(cleaned)
                except ValueError:
                    return 0.0

        def _to_usage_date(value: object) -> date:
            if value is None:
                return start
            raw = str(value).strip()
            if len(raw) == 8 and raw.isdigit():
                try:
                    return datetime.strptime(raw, "%Y%m%d").date()
                except ValueError:
                    return start
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
            return start

        def _build_query(period_start: date, period_end: date) -> QueryDefinition:
            return QueryDefinition(
                type=ExportType.ACTUAL_COST,
                timeframe="Custom",
                time_period=QueryTimePeriod(
                    from_property=datetime(period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc),
                    to=datetime(period_end.year, period_end.month, period_end.day, tzinfo=timezone.utc),
                ),
                dataset=QueryDataset(
                    granularity=GranularityType.DAILY,
                    aggregation={
                        "totalCost": {"name": "PreTaxCost", "function": "Sum"},
                    },
                    grouping=[
                        {"type": "Dimension", "name": "ServiceName"},
                        {"type": "Dimension", "name": "ResourceId"},
                        {"type": "Dimension", "name": "ResourceGroupName"},
                        {"type": "Dimension", "name": "ResourceLocation"},
                    ],
                ),
            )

        def _append_from_result(result_obj) -> None:
            columns = [col.name for col in result_obj.columns]
            for row in result_obj.rows:
                row_dict = dict(zip(columns, row))
                tags = _parse_tags(row_dict.get("Tags"))
                usage_date = _to_usage_date(
                    row_dict.get("UsageDate")
                    or row_dict.get("Date")
                    or row_dict.get("ChargePeriodStart")
                )
                if usage_date < start or usage_date > end:
                    usage_date = start

                cost_value = _to_float(
                    row_dict.get("totalCost")
                    or row_dict.get("TotalCost")
                    or row_dict.get("PreTaxCost")
                    or row_dict.get("Cost")
                    or row_dict.get("CostInBillingCurrency")
                    or row_dict.get("BillingCurrencyCost")
                )
                if cost_value == 0.0:
                    for key, value in row_dict.items():
                        if "cost" in str(key).lower():
                            parsed = _to_float(value)
                            if parsed != 0.0:
                                cost_value = parsed
                                break

                records.append(
                    CanonicalCostRecord(
                        date=usage_date,
                        provider="azure",
                        subscription_id=subscription_id,
                        service=str(row_dict.get("ServiceName", "unknown")),
                        resource_id=str(row_dict.get("ResourceId", "")),
                        resource_name=str(row_dict.get("ResourceGroupName", "")),
                        region=str(row_dict.get("ResourceLocation", "unknown")),
                        environment=_infer_environment(tags),
                        owner_team=_infer_owner_team(tags),
                        cost_usd=cost_value,
                        usage_quantity=_to_float(row_dict.get("UsageQuantity") or row_dict.get("Quantity")),
                        usage_unit=str(row_dict.get("UnitOfMeasure", "")),
                        currency=str(row_dict.get("Currency", "USD")),
                        tags=tags,
                        charge_type=str(row_dict.get("ChargeType", "")),
                        pricing_model=str(row_dict.get("PricingModel", "")),
                        benefit_id=str(row_dict.get("BenefitId") or row_dict.get("ReservationId") or ""),
                        benefit_name=str(row_dict.get("BenefitName") or row_dict.get("ReservationName") or ""),
                        frequency=str(row_dict.get("Frequency", "")),
                        publisher_type=str(row_dict.get("PublisherType", "")),
                        cost_type="actual",
                    )
                )

        try:
            result = await asyncio.to_thread(client.query.usage, scope=scope, parameters=_build_query(start, end))
            _append_from_result(result)
        except Exception as exc:
            if "Too many requests" not in str(exc):
                raise
            log.warning("azure.fetch_costs.rate_limited", subscription=subscription_id, reason=str(exc))
            window_start = start
            while window_start <= end:
                window_end = min(window_start + timedelta(days=29), end)
                try:
                    result = await asyncio.to_thread(
                        client.query.usage, scope=scope, parameters=_build_query(window_start, window_end)
                    )
                    _append_from_result(result)
                except Exception as chunk_exc:
                    log.warning(
                        "azure.fetch_costs.chunk.failed",
                        subscription=subscription_id,
                        start=window_start.isoformat(),
                        end=window_end.isoformat(),
                        reason=str(chunk_exc),
                    )
                window_start = window_end + timedelta(days=1)

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
            log.info(
                "azure.blob_ingest.skipped",
                reason="storage_account_url or cost_export_container not configured",
                storage_account_url=self.storage_account_url,
                cost_export_container=self.cost_export_container,
            )
            return [], []

        log.info(
            "azure.blob_ingest.start",
            subscription=subscription_id,
            storage_account_url=self.storage_account_url,
            container=self.cost_export_container,
            prefix=self.cost_export_prefix or "(none)",
            date_range=f"{start} → {end}",
            already_checkpointed=len(checkpoint_keys) if checkpoint_keys else 0,
        )

        from azure.storage.blob.aio import BlobServiceClient

        cred = self._get_credential()
        records: list[CanonicalCostRecord] = []
        consumed_checkpoints: list[dict[str, str]] = []
        seen_checkpoints: set[str] = set()
        all_blobs_found: list[str] = []
        skipped_unsupported: list[str] = []
        skipped_checkpoint: list[str] = []

        def _is_supported_blob(name: str) -> str | None:
            lower = name.lower()
            if lower.endswith(".csv"):
                return "csv"
            if lower.endswith(".parquet") or lower.endswith(".snappy.parquet"):
                return "parquet"
            return None

        try:
            blob_service = BlobServiceClient(account_url=self.storage_account_url, credential=cred)
            container = blob_service.get_container_client(self.cost_export_container)

            async for blob in container.list_blobs(name_starts_with=self.cost_export_prefix or None):
                blob_name = str(getattr(blob, "name", ""))
                all_blobs_found.append(blob_name)

                blob_format = _is_supported_blob(blob_name)
                if blob_format is None:
                    skipped_unsupported.append(blob_name)
                    continue

                blob_etag = str(getattr(blob, "etag", "") or "")
                checkpoint_key = self._build_blob_checkpoint_key(blob_name, blob_etag)
                if checkpoint_keys and checkpoint_key in checkpoint_keys:
                    skipped_checkpoint.append(blob_name)
                    continue
                if checkpoint_key in seen_checkpoints:
                    skipped_checkpoint.append(blob_name)
                    continue

                log.info(
                    "azure.blob_ingest.processing",
                    blob_name=blob_name,
                    blob_etag=blob_etag,
                    format=blob_format,
                )
                try:
                    downloader = await container.download_blob(blob_name)
                    payload = await downloader.readall()

                    if blob_format == "csv":
                        text = payload.decode("utf-8-sig", errors="replace")
                        parsed = self._parse_blob_cost_csv(text, subscription_id, start, end)
                    else:
                        parsed = self._parse_blob_cost_parquet(payload, subscription_id, start, end)

                    records.extend(parsed)
                    log.info(
                        "azure.blob_ingest.parsed",
                        blob_name=blob_name,
                        blob_etag=blob_etag,
                        format=blob_format,
                        rows_parsed=len(parsed),
                        total_records_so_far=len(records),
                        date_range=f"{start} → {end}",
                        subscription_id=subscription_id,
                    )
                    if not parsed and blob_format == "csv":
                        text = payload.decode("utf-8-sig", errors="replace")
                        first_lines = text.splitlines()[:3]
                        log.warning(
                            "azure.blob_ingest.zero_rows_skipped_checkpoint",
                            blob_name=blob_name,
                            blob_etag=blob_etag,
                            format=blob_format,
                            csv_header=first_lines[0] if first_lines else "(empty file)",
                            csv_sample_row=first_lines[1] if len(first_lines) > 1 else "(no rows)",
                            expected_date_columns="date | usagedate | usage_date",
                            expected_cost_columns="pretaxcost | cost | costusd | costinbillingcurrency",
                            filter_date_range=f"{start} → {end}",
                            filter_subscription_id=subscription_id,
                            action="checkpoint_NOT_recorded",
                        )
                    elif not parsed and blob_format == "parquet":
                        log.warning(
                            "azure.blob_ingest.zero_rows_skipped_checkpoint",
                            blob_name=blob_name,
                            blob_etag=blob_etag,
                            format=blob_format,
                            payload_bytes=len(payload),
                            filter_date_range=f"{start} → {end}",
                            filter_subscription_id=subscription_id,
                            action="checkpoint_NOT_recorded",
                            hint="Parquet file produced 0 records — check date range and column schema.",
                        )
                    if parsed:
                        consumed_checkpoints.append(
                            {
                                "checkpoint_key": checkpoint_key,
                                "blob_name": blob_name,
                                "blob_etag": blob_etag,
                                "rows_parsed": str(len(parsed)),
                            }
                        )
                        seen_checkpoints.add(checkpoint_key)
                    else:
                        log.warning(
                            "azure.blob_ingest.checkpoint_poisoning_prevented",
                            blob_name=blob_name,
                            blob_etag=blob_etag,
                            subscription_id=subscription_id,
                            reason="zero rows parsed — blob will be retried on next sync",
                        )
                except Exception as exc:
                    log.warning(
                        "azure.fetch_costs.blob_item.failed",
                        subscription=subscription_id,
                        blob_name=blob_name,
                        format=blob_format,
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

        supported_count = len(all_blobs_found) - len(skipped_unsupported)
        log.info(
            "azure.blob_ingest.summary",
            subscription=subscription_id,
            container=self.cost_export_container,
            prefix=self.cost_export_prefix or "(none)",
            total_blobs_listed=len(all_blobs_found),
            supported_blobs_found=supported_count,
            skipped_unsupported_format=len(skipped_unsupported),
            skipped_already_checkpointed=len(skipped_checkpoint),
            blobs_processed=len(consumed_checkpoints),
            total_records_parsed=len(records),
        )

        if not all_blobs_found:
            expected_path = f"{self.storage_account_url}/{self.cost_export_container}/{self.cost_export_prefix or ''}*.(csv|parquet)"
            log.warning(
                "azure.blob_ingest.no_blobs_found",
                subscription=subscription_id,
                container=self.cost_export_container,
                prefix_used=self.cost_export_prefix or "(none)",
                expected_path=expected_path,
                hint="Check that Cost Management Exports has generated files and the prefix matches the export path.",
            )
        elif not records:
            log.warning(
                "azure.blob_ingest.no_records_inserted",
                subscription=subscription_id,
                blobs_listed=all_blobs_found,
                blobs_processed=len(consumed_checkpoints),
                hint="Files were found but produced 0 records — check date range filter and subscription_id filter.",
            )

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
    def _parse_blob_cost_parquet(
        raw_bytes: bytes,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCostRecord]:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            log.error("azure.blob_ingest.parquet.import_failed", hint="pyarrow is not installed")
            return []

        try:
            table = pq.read_table(io.BytesIO(raw_bytes))
        except Exception as exc:
            log.warning("azure.blob_ingest.parquet.read_failed", error=type(exc).__name__, reason=str(exc)[:200])
            return []

        columns = [str(c) for c in table.column_names]
        log.info(
            "azure.blob_ingest.parquet.schema",
            columns=columns[:30],
            num_columns=len(columns),
            num_rows=table.num_rows,
        )

        date_columns_normalized: list[str] = []
        for col_name in columns:
            col = table.column(col_name)
            if pa.types.is_timestamp(col.type):
                if col.type.unit == "ns":
                    table = table.set_column(
                        table.schema.get_field_index(col_name),
                        col_name,
                        col.cast(pa.timestamp("us"), safe=False),
                    )
                    date_columns_normalized.append(col_name)

        if date_columns_normalized:
            log.info(
                "azure.blob_ingest.parquet.date_columns_normalized",
                columns=date_columns_normalized,
                action="cast timestamp[ns] -> timestamp[us]",
            )

        rows: list[CanonicalCostRecord] = []
        for batch in table.to_batches(max_chunksize=5000):
            batch_dict = batch.to_pydict()
            num_rows_in_batch = len(next(iter(batch_dict.values()))) if batch_dict else 0
            for i in range(num_rows_in_batch):
                row = {}
                for col in columns:
                    val = batch_dict[col][i]
                    if val is None:
                        row[col] = ""
                    elif isinstance(val, (date, datetime)):
                        row[col] = val.isoformat() if hasattr(val, "isoformat") else str(val)
                    else:
                        row[col] = str(val)
                normalized = AzureConnectorClient._normalize_blob_cost_row(row, subscription_id, start, end)
                if normalized:
                    rows.append(normalized)

        log.info(
            "azure.blob_ingest.parquet.parsed",
            records_parsed=len(rows),
            date_columns_normalized=date_columns_normalized,
        )

        return rows

    @staticmethod
    def _normalize_blob_cost_row(
        row: dict,
        fallback_subscription_id: str,
        start: date,
        end: date,
    ) -> CanonicalCostRecord | None:
        def _normalize_key(key: object) -> str:
            raw = str(key).strip().lower()
            # Normalize variations like "Cost In Billing Currency", "cost_in_billing_currency",
            # or "cost-in-billing-currency" to the same token.
            return "".join(ch for ch in raw if ch.isalnum())

        normalized = {_normalize_key(k): ("" if v is None else str(v).strip()) for k, v in row.items()}

        usage_date_raw = normalized.get("date") or normalized.get("usagedate") or normalized.get("usage_date")
        if not usage_date_raw:
            return None

        usage_date = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S+00:00"):
            try:
                usage_date = datetime.strptime(usage_date_raw, fmt).date()
                break
            except ValueError:
                continue
        if usage_date is None:
            # Last resort: try parsing just the date prefix (handles any ISO variant)
            try:
                usage_date = datetime.strptime(usage_date_raw[:10], "%Y-%m-%d").date()
            except (ValueError, IndexError):
                pass
        if usage_date is None:
            return None
        if usage_date < start or usage_date > end:
            return None

        record_subscription_id = (
            normalized.get("subscriptionid")
            or normalized.get("subscription_id")
            or fallback_subscription_id
        )

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
                    pass

                # Handle localized/currency strings such as:
                # "1.234,56", "R$ 1,234.56", "(123,45)".
                raw = value.strip()
                if not raw:
                    continue

                negative = raw.startswith("(") and raw.endswith(")")
                raw = raw.strip("()")
                cleaned = "".join(ch for ch in raw if ch.isdigit() or ch in ",.-")
                if not cleaned:
                    continue

                if "," in cleaned and "." in cleaned:
                    # Keep the right-most separator as decimal separator.
                    if cleaned.rfind(",") > cleaned.rfind("."):
                        cleaned = cleaned.replace(".", "").replace(",", ".")
                    else:
                        cleaned = cleaned.replace(",", "")
                elif "," in cleaned and "." not in cleaned:
                    cleaned = cleaned.replace(",", ".")

                try:
                    parsed = float(cleaned)
                    return -parsed if negative else parsed
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
            cost_usd=_float_value(
                "pretaxcost",
                "cost",
                "costusd",
                "costinbillingcurrency",
                "billingcurrencycost",
                "effectivecost",
                "amortizedcost",
            ),
            usage_quantity=_float_value("usagequantity", "quantity", "consumedquantity", "billedquantity"),
            usage_unit=normalized.get("unitofmeasure") or normalized.get("usageunit") or normalized.get("unit") or "",
            currency=normalized.get("currency") or "USD",
            tags=tags,
            charge_type=normalized.get("chargetype") or normalized.get("charge_type") or "",
            pricing_model=normalized.get("pricingmodel") or normalized.get("pricing_model") or "",
            benefit_id=(
                normalized.get("benefitid")
                or normalized.get("benefit_id")
                or normalized.get("reservationid")
                or normalized.get("reservation_id")
                or ""
            ),
            benefit_name=(
                normalized.get("benefitname")
                or normalized.get("benefit_name")
                or normalized.get("reservationname")
                or normalized.get("reservation_name")
                or ""
            ),
            frequency=normalized.get("frequency") or "",
            publisher_type=normalized.get("publishertype") or normalized.get("publisher_type") or "",
            cost_type="actual",
        )

    async def fetch_events(
        self, subscription_id: str, start: date, end: date
    ) -> list[CanonicalEventRecord]:
        from azure.mgmt.monitor import MonitorManagementClient

        cred = self._get_credential()
        client = MonitorManagementClient(cred, subscription_id)

        safe_start = max(start, date.today() - timedelta(days=89))
        filter_str = (
            f"eventTimestamp ge '{safe_start.isoformat()}T00:00:00Z' "
            f"and eventTimestamp le '{end.isoformat()}T23:59:59Z'"
        )
        events = await asyncio.to_thread(
            lambda: list(
                itertools.islice(
                    client.activity_logs.list(
                        filter=filter_str,
                        select="eventTimestamp,operationName,resourceId,resourceGroupName,resourceProviderName,status,caller,correlationId,level,description",
                    ),
                    1000,
                )
            )
        )

        records: list[CanonicalEventRecord] = []
        def _enum_or_str(value: object, default: str) -> str:
            if value is None:
                return default
            return str(getattr(value, "value", value))

        for ev in events:
            ts = ev.event_timestamp or datetime.now(timezone.utc)
            records.append(
                CanonicalEventRecord(
                    timestamp=ts,
                    provider="azure",
                    subscription_id=subscription_id,
                    event_type=_enum_or_str(ev.operation_name, "unknown"),
                    resource_id=str(ev.resource_id or ""),
                    resource_name=str(ev.resource_group_name or ""),
                    region="azure",
                    severity=_enum_or_str(ev.level, "informational"),
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

    async def fetch_recommendations(
        self, subscription_id: str
    ) -> list[CanonicalRecommendationRecord]:
        """Fetch Azure Advisor recommendations for the subscription."""
        from azure.mgmt.advisor import AdvisorManagementClient

        cred = self._get_credential()
        client = AdvisorManagementClient(cred, subscription_id)
        now = datetime.now(timezone.utc)
        records: list[CanonicalRecommendationRecord] = []

        try:
            recs = await asyncio.to_thread(lambda: list(client.recommendations.list()))
            categories_seen: dict[str, int] = {}
            for rec in recs:
                cat = str(getattr(rec, "category", "") or "")
                categories_seen[cat] = categories_seen.get(cat, 0) + 1

                rec_id = str(rec.id or "")

                # The Advisor resource ID is structured as:
                # /subscriptions/{sub}/resourceGroups/{rg}/providers/{type}/{name}
                # /providers/Microsoft.Advisor/recommendations/{rec_uuid}
                # Split on the Advisor segment to extract the impacted resource path.
                advisor_marker = "/providers/Microsoft.Advisor/recommendations/"
                if advisor_marker in rec_id:
                    resource_id = rec_id.split(advisor_marker)[0]
                else:
                    resource_id = ""

                # Fall back to resource_metadata if available
                if not resource_id:
                    meta = getattr(rec, "resource_metadata", None)
                    resource_id = str(getattr(meta, "resource_id", "") or "")

                resource_group = ""
                if "/resourceGroups/" in resource_id:
                    resource_group = resource_id.split("/resourceGroups/")[1].split("/")[0]

                resource_name = (
                    resource_id.split("/")[-1]
                    if resource_id
                    else str(getattr(rec, "impacted_value", "") or "")
                )

                # Extract human-readable description
                short_desc_obj = getattr(rec, "short_description", None)
                short_description = ""
                if short_desc_obj:
                    short_description = str(
                        getattr(short_desc_obj, "problem", "")
                        or getattr(short_desc_obj, "solution", "")
                        or ""
                    )

                # Estimated savings live in extended_properties under various keys
                extended = getattr(rec, "extended_properties", None) or {}
                savings: float | None = None
                savings_period = "annual"
                for key in ("savingsAmount", "annualSavingsAmount", "estimatedAnnualSavings"):
                    raw = extended.get(key)
                    if raw is not None:
                        try:
                            savings = float(raw)
                            savings_period = "monthly" if key == "savingsAmount" else "annual"
                            break
                        except (TypeError, ValueError):
                            continue

                records.append(
                    CanonicalRecommendationRecord(
                        recommendation_id=str(rec.name or rec_id.split("/")[-1] or ""),
                        provider="azure",
                        subscription_id=subscription_id,
                        category=str(getattr(rec, "category", "") or ""),
                        impact=str(getattr(rec, "impact", "") or ""),
                        resource_id=resource_id,
                        resource_name=resource_name,
                        resource_group=resource_group,
                        service=str(getattr(rec, "impacted_field", "") or ""),
                        short_description=short_description,
                        recommendation_type_id=str(getattr(rec, "recommendation_type_id", "") or ""),
                        estimated_savings_usd=savings,
                        fetched_at=now,
                        savings_period=savings_period,
                    )
                )
        except Exception as exc:
            log.warning(
                "azure.fetch_recommendations.failed",
                subscription=subscription_id,
                reason=str(exc),
                exc_type=type(exc).__name__,
            )
            return []

        log.info(
            "azure.fetch_recommendations.done",
            subscription=subscription_id,
            total_from_api=len(recs),
            records=len(records),
            categories=categories_seen,
            cost_recs=categories_seen.get("Cost", 0),
        )
        return records

    async def fetch_inventory(
        self, subscription_id: str
    ) -> list[CanonicalResourceRecord]:
        """Fetch all deployed resources via Azure Resource Graph."""
        from azure.mgmt.resourcegraph import ResourceGraphClient
        from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

        cred = self._get_credential()
        client = ResourceGraphClient(cred)
        now = datetime.now(timezone.utc)

        KQL = """
        Resources
        | project id, name, type, resourceGroup, location, tags, sku, properties
        | order by type asc
        """

        records: list[CanonicalResourceRecord] = []
        skip_token: str | None = None

        try:
            while True:
                options = QueryRequestOptions(top=1000, skip_token=skip_token)
                request = QueryRequest(
                    subscriptions=[subscription_id],
                    query=KQL,
                    options=options,
                )
                result = client.resources(request)

                for row in result.data or []:
                    if not isinstance(row, dict):
                        continue
                    tags = _parse_tags(row.get("tags") or {})
                    sku = row.get("sku") or {}
                    props = row.get("properties") or {}

                    records.append(
                        CanonicalResourceRecord(
                            resource_id=str(row.get("id") or ""),
                            provider="azure",
                            subscription_id=subscription_id,
                            name=str(row.get("name") or ""),
                            resource_type=str(row.get("type") or ""),
                            resource_group=str(row.get("resourceGroup") or ""),
                            location=str(row.get("location") or "unknown"),
                            environment=_infer_environment(tags),
                            owner_team=_infer_owner_team(tags),
                            sku_name=str(sku.get("name") or "") if isinstance(sku, dict) else "",
                            sku_tier=str(sku.get("tier") or "") if isinstance(sku, dict) else "",
                            provisioning_state=str(props.get("provisioningState") or "") if isinstance(props, dict) else "",
                            tags=tags,
                            fetched_at=now,
                        )
                    )

                skip_token = getattr(result, "skip_token", None)
                if not skip_token or len(result.data or []) < 1000:
                    break

        except Exception as exc:
            log.warning(
                "azure.fetch_inventory.failed",
                subscription=subscription_id,
                reason=str(exc),
            )
            return []

        log.info(
            "azure.fetch_inventory.done",
            subscription=subscription_id,
            records=len(records),
        )
        return records

    async def fetch_usage_metrics(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalUsageRecord]:
        """Fetch daily CPU/network metrics for VMs via Azure Monitor."""
        from azure.mgmt.monitor import MonitorManagementClient
        from azure.mgmt.resource import ResourceManagementClient

        cred = self._get_credential()
        resource_client = ResourceManagementClient(cred, subscription_id)
        monitor_client = MonitorManagementClient(cred, subscription_id)

        timespan = f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z"
        METRICS = "Percentage CPU,Network In Total,Network Out Total,Disk Read Bytes,Disk Write Bytes"

        records: list[CanonicalUsageRecord] = []

        try:
            vms = await asyncio.to_thread(
                lambda: list(
                    resource_client.resources.list(
                        filter="resourceType eq 'Microsoft.Compute/virtualMachines'",
                        top=100,
                    )
                )
            )
        except Exception as exc:
            log.warning(
                "azure.fetch_usage.list_vms_failed",
                subscription=subscription_id,
                reason=str(exc),
            )
            return []

        for vm in vms:
            try:
                metrics_result = await asyncio.to_thread(
                    lambda: monitor_client.metrics.list(
                        resource_uri=vm.id,
                        timespan=timespan,
                        interval="P1D",
                        metricnames=METRICS,
                        aggregation="Average",
                    )
                )
                tags = _parse_tags(vm.tags)
                environment = _infer_environment(tags)

                for metric in metrics_result.value:
                    metric_name = (
                        metric.name.localized_value
                        or metric.name.value
                        or ""
                    )
                    metric_unit = metric.unit.value if metric.unit else ""

                    for ts in metric.timeseries:
                        for point in ts.data:
                            if point.average is None:
                                continue
                            records.append(
                                CanonicalUsageRecord(
                                    date=point.time_stamp.date(),
                                    provider="azure",
                                    subscription_id=subscription_id,
                                    service="Virtual Machines",
                                    resource_id=str(vm.id or ""),
                                    metric_name=metric_name,
                                    metric_value=round(point.average, 6),
                                    metric_unit=metric_unit,
                                    region=str(vm.location or "unknown"),
                                    environment=environment,
                                )
                            )
            except Exception as exc:
                log.warning(
                    "azure.fetch_usage.vm_metrics_failed",
                    vm_id=str(vm.id),
                    reason=str(exc),
                )
                continue

        log.info(
            "azure.fetch_usage.done",
            subscription=subscription_id,
            records=len(records),
        )
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
