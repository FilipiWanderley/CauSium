from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
import re
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query, insert_rows
from app.core.logging import get_logger
from app.domains.cloud_accounts.service import CloudAccountService
from app.domains.connectors.base import CanonicalEventRecord
from app.domains.cloud_ledger.schemas import (
    CostRow,
    CostSummary,
    CostTrend,
    DashboardMetrics,
    DetailedCostRow,
    IngestResult,
    ReservationCoverageByService,
    ReservationCoverageSummary,
    ReservationEfficiencyByFamily,
    ReservationEfficiencySummary,
    ServiceBreakdown,
)

log = get_logger(__name__)


def _normalize_provider_event(event_type: str) -> str:
    return event_type.strip().lower()


def _is_vm_start_event(normalized_event_type: str) -> bool:
    return (
        normalized_event_type in {"startinstances"}
        or "virtualmachines/start/action" in normalized_event_type
        or ".instances.start" in normalized_event_type
    )


def _is_vm_stop_event(normalized_event_type: str) -> bool:
    return (
        normalized_event_type in {"stopinstances", "terminateinstances", "rebootinstances"}
        or "virtualmachines/deallocate/action" in normalized_event_type
        or "virtualmachines/poweroff/action" in normalized_event_type
        or "virtualmachines/stop/action" in normalized_event_type
        or ".instances.stop" in normalized_event_type
        or ".instances.delete" in normalized_event_type
    )


def _is_resource_create_event(normalized_event_type: str) -> bool:
    return (
        normalized_event_type.startswith("create")
        or normalized_event_type.startswith("runinstances")
        or normalized_event_type.endswith("/write")
        or normalized_event_type.endswith(".insert")
        or normalized_event_type.endswith(".create")
    )


class CloudLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_account(
        self, org_id: UUID, account_id: UUID, start: date, end: date
    ) -> IngestResult:
        from app.domains.cloud_accounts.models import CloudProvider, ConnectorStatus
        from app.domains.connectors.aws.client import AwsConnectorClient
        from app.domains.connectors.azure.client import AzureConnectorClient
        from app.domains.connectors.factory import get_connector_for_account
        from app.domains.cloud_accounts.models import AwsCurIngestionCheckpoint, BlobIngestionCheckpoint

        account_service = CloudAccountService(self.db)
        account = await account_service.get_account(org_id, account_id)
        if not account:
            return IngestResult(account_id=account_id, cost_records=0, event_records=0, status="error", message="Account not found")

        try:
            creds = await account_service.get_azure_credentials(account)
            if account.provider == CloudProvider.AWS:
                creds = await account_service.get_aws_credentials(account)
            if account.provider == CloudProvider.GCP:
                creds = await account_service.get_gcp_credentials(account)
            client = get_connector_for_account(account, creds)

            checkpoint_keys: set[str] | None = None
            aws_checkpoint_keys: set[str] | None = None
            if isinstance(client, AzureConnectorClient):
                checkpoint_keys = await self._get_blob_checkpoint_keys(account.id)
            if isinstance(client, AwsConnectorClient):
                aws_checkpoint_keys = await self._get_aws_cur_checkpoint_keys(account.id)

            costs = []
            events = []
            fetch_errors: list[str] = []

            try:
                if isinstance(client, AzureConnectorClient):
                    costs = await client.fetch_costs(
                        account.external_id,
                        start,
                        end,
                        checkpoint_keys=checkpoint_keys,
                    )
                elif isinstance(client, AwsConnectorClient):
                    costs = await client.fetch_costs(
                        account.external_id,
                        start,
                        end,
                        checkpoint_keys=aws_checkpoint_keys,
                    )
                else:
                    costs = await client.fetch_costs(account.external_id, start, end)
            except Exception as e:
                fetch_errors.append(f"costs: {e}")
                log.warning("ledger.ingest.cost_fetch_failed", account_id=str(account_id), error=str(e))

            try:
                events = await client.fetch_events(account.external_id, start, end)
            except Exception as e:
                fetch_errors.append(f"events: {e}")
                log.warning("ledger.ingest.event_fetch_failed", account_id=str(account_id), error=str(e))

            if not costs and not events and fetch_errors:
                account.status = ConnectorStatus.ERROR
                account.last_sync_at = datetime.now(timezone.utc)
                await self.db.flush()
                return IngestResult(
                    account_id=account_id,
                    cost_records=0,
                    event_records=0,
                    status="error",
                    message="; ".join(fetch_errors),
                )

            blob_checkpoints: list[dict[str, str]] = []
            aws_cur_checkpoints: list[dict[str, str]] = []
            if isinstance(client, AzureConnectorClient):
                blob_checkpoints = client.consume_last_blob_checkpoints()
            if isinstance(client, AwsConnectorClient):
                aws_cur_checkpoints = client.consume_last_cur_checkpoints()

            if not costs and not events and not fetch_errors:
                from app.domains.cloud_accounts.models import ConnectorHealth

                empty_hint = None
                if isinstance(client, AzureConnectorClient) and not blob_checkpoints:
                    empty_hint = (
                        "No Azure Cost export files found. Verify Storage Account URL, container and prefix, "
                        "and ensure Cost Management Exports has generated files (may take hours after setup)."
                    )
                if isinstance(client, AwsConnectorClient) and not aws_cur_checkpoints:
                    empty_hint = (
                        "No AWS CUR objects found. Verify CUR bucket/prefix and that the report is being delivered."
                    )
                if empty_hint:
                    account.status = ConnectorStatus.ERROR
                    account.last_sync_at = datetime.now(timezone.utc)
                    self.db.add(
                        ConnectorHealth(
                            account_id=account_id,
                            status=ConnectorStatus.ERROR,
                            message=empty_hint,
                        )
                    )
                    await self.db.flush()
                    return IngestResult(
                        account_id=account_id,
                        cost_records=0,
                        event_records=0,
                        status="error",
                        message=empty_hint,
                    )

            # Write costs to ClickHouse
            cost_rows = [
                {
                    "date": r.date,
                    "org_id": str(org_id),
                    "account_id": str(account_id),
                    "provider": r.provider,
                    "subscription_id": r.subscription_id,
                    "service": r.service,
                    "resource_id": r.resource_id,
                    "resource_name": r.resource_name,
                    "region": r.region,
                    "environment": r.environment,
                    "owner_team": r.owner_team,
                    "cost_usd": r.cost_usd,
                    "usage_quantity": r.usage_quantity,
                    "usage_unit": r.usage_unit,
                    "currency": r.currency,
                    "tags": r.tags,
                    "tags_map": r.tags if isinstance(r.tags, dict) else {},
                }
                for r in costs
            ]
            if cost_rows:
                try:
                    insert_rows("cost_facts", cost_rows)
                except Exception as e:
                    log.warning("ledger.clickhouse.cost_insert_failed", error=str(e))
                    account.status = ConnectorStatus.ERROR
                    account.last_sync_at = datetime.now(timezone.utc)
                    await self.db.flush()
                    return IngestResult(
                        account_id=account_id,
                        cost_records=0,
                        event_records=0,
                        status="error",
                        message=f"Cost insert failed: {e}",
                    )

            # Write events
            event_rows = [
                {
                    "timestamp": r.timestamp,
                    "org_id": str(org_id),
                    "account_id": str(account_id),
                    "provider": r.provider,
                    "subscription_id": r.subscription_id,
                    "event_type": r.event_type,
                    "resource_id": r.resource_id,
                    "resource_name": r.resource_name,
                    "region": r.region,
                    "severity": r.severity,
                    "description": r.description,
                    "caller": r.caller,
                    "correlation_id": r.correlation_id,
                    "raw_data": r.raw_data,
                }
                for r in events
            ]
            if event_rows:
                try:
                    insert_rows("event_facts", event_rows)
                except Exception as e:
                    log.warning("ledger.clickhouse.event_insert_failed", error=str(e))
                await self._emit_realtime_cloud_event_notifications(
                    org_id=org_id,
                    account_id=account_id,
                    events=events,
                )

            if blob_checkpoints:
                existing_keys = await self._get_blob_checkpoint_keys(account_id)
                for item in blob_checkpoints:
                    key = item.get("checkpoint_key", "")
                    if not key or key in existing_keys:
                        continue
                    self.db.add(
                        BlobIngestionCheckpoint(
                            org_id=org_id,
                            account_id=account_id,
                            provider=account.provider,
                            checkpoint_key=key,
                            blob_name=item.get("blob_name", ""),
                            blob_etag=item.get("blob_etag") or None,
                            records_ingested=len(cost_rows),
                        )
                    )
                    existing_keys.add(key)

            if aws_cur_checkpoints:
                existing_keys = await self._get_aws_cur_checkpoint_keys(account_id)
                for item in aws_cur_checkpoints:
                    key = item.get("checkpoint_key", "")
                    if not key or key in existing_keys:
                        continue
                    self.db.add(
                        AwsCurIngestionCheckpoint(
                            org_id=org_id,
                            account_id=account_id,
                            provider=account.provider,
                            checkpoint_key=key,
                            object_key=item.get("object_key", ""),
                            object_etag=item.get("object_etag") or None,
                            records_ingested=len(cost_rows),
                        )
                    )
                    existing_keys.add(key)

            # Provider advanced ingestion: recommendations, inventory, usage metrics
            recommendation_count = 0
            inventory_count = 0
            usage_count = 0

            recommendation_count = await self._ingest_provider_recommendations(
                client, org_id, account_id, account.external_id
            )
            inventory_count = await self._ingest_provider_inventory(
                client, org_id, account_id, account.external_id
            )
            usage_count = await self._ingest_provider_usage_metrics(
                client, org_id, account_id, account.external_id, start, end
            )

            account.status = ConnectorStatus.ACTIVE
            account.last_sync_at = datetime.now(timezone.utc)
            await self.db.flush()

            log.info(
                "ledger.ingest.done",
                account_id=str(account_id),
                costs=len(costs),
                events=len(events),
                recommendations=recommendation_count,
                inventory=inventory_count,
                usage=usage_count,
            )
            return IngestResult(
                account_id=account_id,
                cost_records=len(costs),
                event_records=len(events),
                recommendation_records=recommendation_count,
                inventory_records=inventory_count,
                usage_records=usage_count,
                status="ok",
            )
        except Exception as exc:
            account.status = ConnectorStatus.ERROR
            account.last_sync_at = datetime.now(timezone.utc)
            await self.db.flush()
            log.exception("ledger.ingest.failed", account_id=str(account_id), error=str(exc))
            return IngestResult(
                account_id=account_id,
                cost_records=0,
                event_records=0,
                status="error",
                message=str(exc)[:500],
            )

    async def _emit_realtime_cloud_event_notifications(
        self,
        *,
        org_id: UUID,
        account_id: UUID,
        events: list[CanonicalEventRecord],
    ) -> None:
        from app.domains.notifications.models import AlertCategory, AlertSeverity
        from app.domains.notifications.service import NotificationsService

        service = NotificationsService(self.db)
        max_notifications_per_batch = 200
        emitted = 0

        for event in events:
            normalized_event_type = _normalize_provider_event(event.event_type or "")
            if not normalized_event_type:
                continue

            if _is_vm_start_event(normalized_event_type):
                normalized_alert_type = "cloud.vm.started"
                severity = AlertSeverity.INFO
            elif _is_vm_stop_event(normalized_event_type):
                normalized_alert_type = "cloud.vm.stopped"
                severity = AlertSeverity.WARNING
            elif _is_resource_create_event(normalized_event_type):
                normalized_alert_type = "cloud.resource.created"
                severity = AlertSeverity.INFO
            else:
                continue

            resource_ref = event.resource_name or event.resource_id or "resource"
            title = f"{event.provider.upper()}: {normalized_alert_type} - {resource_ref}"
            body = event.description or f"Detected event {event.event_type}"
            source_id = event.correlation_id or (
                f"{event.provider}:{event.event_type}:{event.resource_id}:"
                f"{getattr(event.timestamp, 'isoformat', lambda: str(event.timestamp))()}"
            )

            await service.create_realtime_alert(
                org_id=org_id,
                category=AlertCategory.ACTIVITY,
                severity=severity,
                event_type=normalized_alert_type,
                title=title,
                body=body,
                source_type="cloud_event",
                source_id=source_id,
                extra_metadata={
                    "provider_event_type": event.event_type,
                    "provider": event.provider,
                    "resource_id": event.resource_id,
                    "resource_name": event.resource_name,
                    "account_id": str(account_id),
                },
            )

            emitted += 1
            if emitted >= max_notifications_per_batch:
                log.info(
                    "ledger.cloud_event_notifications.capped",
                    account_id=str(account_id),
                    emitted=emitted,
                    total_events=len(events),
                )
                break

    async def _ingest_provider_recommendations(
        self,
        client,
        org_id,
        account_id,
        subscription_id: str,
    ) -> int:
        fetch_recommendations = getattr(client, "fetch_recommendations", None)
        if not callable(fetch_recommendations):
            return 0
        try:
            recs = await fetch_recommendations(subscription_id)
        except Exception as exc:
            log.warning("ledger.provider_recommendations.fetch_failed", error=str(exc))
            return 0

        rows = [
            {
                "fetched_at": r.fetched_at,
                "org_id": str(org_id),
                "account_id": str(account_id),
                "provider": r.provider,
                "subscription_id": r.subscription_id,
                "recommendation_id": r.recommendation_id,
                "category": r.category,
                "impact": r.impact,
                "resource_id": r.resource_id,
                "resource_name": r.resource_name,
                "resource_group": r.resource_group,
                "service": r.service,
                "short_description": r.short_description,
                "recommendation_type_id": r.recommendation_type_id,
                "estimated_savings_usd": r.estimated_savings_usd,
            }
            for r in recs
        ]
        if rows:
            try:
                insert_rows("recommendation_facts", rows)
            except Exception as exc:
                log.warning("ledger.clickhouse.recommendation_insert_failed", error=str(exc))
                return 0

        return len(rows)

    async def _ingest_provider_inventory(
        self,
        client,
        org_id,
        account_id,
        subscription_id: str,
    ) -> int:
        fetch_inventory = getattr(client, "fetch_inventory", None)
        if not callable(fetch_inventory):
            return 0
        try:
            resources = await fetch_inventory(subscription_id)
        except Exception as exc:
            log.warning("ledger.provider_inventory.fetch_failed", error=str(exc))
            return 0

        rows = [
            {
                "fetched_at": r.fetched_at,
                "org_id": str(org_id),
                "account_id": str(account_id),
                "provider": r.provider,
                "subscription_id": r.subscription_id,
                "resource_id": r.resource_id,
                "name": r.name,
                "resource_type": r.resource_type,
                "resource_group": r.resource_group,
                "location": r.location,
                "environment": r.environment,
                "owner_team": r.owner_team,
                "sku_name": r.sku_name,
                "sku_tier": r.sku_tier,
                "provisioning_state": r.provisioning_state,
                "tags": r.tags,
                "tags_map": r.tags if isinstance(r.tags, dict) else {},
            }
            for r in resources
        ]
        if rows:
            try:
                insert_rows("resource_inventory", rows)
            except Exception as exc:
                log.warning("ledger.clickhouse.inventory_insert_failed", error=str(exc))
                return 0

        return len(rows)

    async def _ingest_provider_usage_metrics(
        self,
        client,
        org_id,
        account_id,
        subscription_id: str,
        start,
        end,
    ) -> int:
        fetch_usage_metrics = getattr(client, "fetch_usage_metrics", None)
        if not callable(fetch_usage_metrics):
            return 0
        try:
            usage = await fetch_usage_metrics(subscription_id, start, end)
        except Exception as exc:
            log.warning("ledger.provider_usage.fetch_failed", error=str(exc))
            return 0

        rows = [
            {
                "date": r.date,
                "org_id": str(org_id),
                "account_id": str(account_id),
                "provider": r.provider,
                "subscription_id": r.subscription_id,
                "service": r.service,
                "resource_id": r.resource_id,
                "metric_name": r.metric_name,
                "metric_value": r.metric_value,
                "metric_unit": r.metric_unit,
                "region": r.region,
                "environment": r.environment,
            }
            for r in usage
        ]
        if rows:
            try:
                insert_rows("usage_facts", rows)
            except Exception as exc:
                log.warning("ledger.clickhouse.usage_insert_failed", error=str(exc))
                return 0

        return len(rows)

    async def ingest_carbon_account(
        self,
        org_id: UUID,
        account_id: UUID,
        start: date,
        end: date,
    ) -> int:
        from app.domains.cloud_accounts.models import CloudProvider
        from app.domains.connectors.factory import get_connector_for_account

        account_service = CloudAccountService(self.db)
        account = await account_service.get_account(org_id, account_id)
        if not account:
            raise ValueError("Account not found")

        creds = await account_service.get_azure_credentials(account)
        if account.provider == CloudProvider.AWS:
            creds = await account_service.get_aws_credentials(account)
        if account.provider == CloudProvider.GCP:
            creds = await account_service.get_gcp_credentials(account)
        client = get_connector_for_account(account, creds)

        carbon = await client.fetch_carbon_emissions(account.external_id, start, end)
        carbon_rows = [
            {
                "year_month": r.year_month,
                "org_id": str(org_id),
                "account_id": str(account_id),
                "provider": r.provider,
                "subscription_id": r.subscription_id,
                "service": r.service,
                "resource_group": r.resource_group,
                "kg_co2e": r.kg_co2e,
            }
            for r in carbon
        ]

        if carbon_rows:
            insert_rows("carbon_facts", carbon_rows)

        account.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()
        log.info("ledger.carbon_ingest.done", account_id=str(account_id), carbon_records=len(carbon_rows))
        return len(carbon_rows)

    async def _get_blob_checkpoint_keys(self, account_id: UUID) -> set[str]:
        from app.domains.cloud_accounts.models import BlobIngestionCheckpoint

        result = await self.db.execute(
            select(BlobIngestionCheckpoint.checkpoint_key).where(
                BlobIngestionCheckpoint.account_id == account_id
            )
        )
        return {row[0] for row in result.all()}

    async def _get_aws_cur_checkpoint_keys(self, account_id: UUID) -> set[str]:
        from app.domains.cloud_accounts.models import AwsCurIngestionCheckpoint

        result = await self.db.execute(
            select(AwsCurIngestionCheckpoint.checkpoint_key).where(
                AwsCurIngestionCheckpoint.account_id == account_id
            )
        )
        return {row[0] for row in result.all()}

    def get_cost_trend(
        self,
        org_id: UUID,
        days: int = 30,
        provider: str | None = None,
    ) -> list[CostTrend]:
        end = date.today()
        start = end - timedelta(days=days)
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {"org_id": str(org_id), "start": start, "end": end}
        if provider:
            params["provider"] = provider
        try:
            rows = execute_query(
                f"""
                SELECT date, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                  {provider_where}
                GROUP BY date
                ORDER BY date
                """,
                params,
            )
            return [CostTrend(date=r["date"], cost_usd=r["cost_usd"]) for r in rows]
        except Exception as e:
            log.warning("ledger.cost_trend.failed", error=str(e))
            return []

    def get_detailed_costs(
        self,
        org_id: UUID,
        *,
        days: int = 30,
        service: str | None = None,
        provider: str | None = None,
        owner_team: str | None = None,
        environment: str | None = None,
        region: str | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        account_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DetailedCostRow], int]:
        end = date.today()
        start = end - timedelta(days=days)

        where_parts = [
            "org_id = {org_id:String}",
            "date >= {start:Date}",
            "date <= {end:Date}",
        ]
        params: dict[str, object] = {
            "org_id": str(org_id),
            "start": start,
            "end": end,
            "limit": limit,
            "offset": offset,
        }

        filters = {
            "service": service,
            "provider": provider,
            "owner_team": owner_team,
            "environment": environment,
            "region": region,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "account_id": account_id,
        }
        for field_name, field_value in filters.items():
            if field_value:
                where_parts.append(f"{field_name} = {{{field_name}:String}}")
                params[field_name] = field_value

        where_clause = " AND ".join(where_parts)

        try:
            count_start = perf_counter()
            count_rows = execute_query(
                f"""
                SELECT count() AS total
                FROM cost_facts
                PREWHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                {f"WHERE {' AND '.join(where_parts[3:])}" if len(where_parts) > 3 else ""}
                """,
                params,
            )
            total = int(count_rows[0]["total"]) if count_rows else 0
            count_ms = round((perf_counter() - count_start) * 1000, 2)

            data_start = perf_counter()
            rows = execute_query(
                f"""
                SELECT
                    date,
                    account_id,
                    provider,
                    subscription_id,
                    service,
                    resource_id,
                    resource_name,
                    region,
                    environment,
                    owner_team,
                    cost_usd,
                    usage_quantity,
                    usage_unit,
                    currency
                FROM cost_facts
                PREWHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                {f"WHERE {' AND '.join(where_parts[3:])}" if len(where_parts) > 3 else ""}
                ORDER BY date DESC, cost_usd DESC, resource_id ASC
                LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
                """,
                params,
            )
            data_ms = round((perf_counter() - data_start) * 1000, 2)

            log.info(
                "ledger.detailed_costs.query",
                org_id=str(org_id),
                days=days,
                filters={k: v for k, v in filters.items() if v},
                page_size=limit,
                offset=offset,
                total=total,
                rows=len(rows),
                count_ms=count_ms,
                data_ms=data_ms,
            )

            return (
                [DetailedCostRow(**row) for row in rows],
                total,
            )
        except Exception as exc:
            log.warning("ledger.detailed_costs.failed", error=str(exc))
            return [], 0

    def get_top_services(
        self,
        org_id: UUID,
        days: int = 30,
        limit: int = 10,
        offset: int = 0,
        provider: str | None = None,
    ) -> tuple[list[ServiceBreakdown], int]:
        end = date.today()
        start = end - timedelta(days=days)
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {
            "org_id": str(org_id),
            "start": start,
            "end": end,
            "limit": limit,
            "offset": offset,
        }
        if provider:
            params["provider"] = provider
        try:
            # Total count
            total_rows = execute_query(
                f"""
                SELECT count(DISTINCT service) as total
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                  {provider_where}
                """,
                params,
            )
            total = int(total_rows[0]["total"]) if total_rows else 0

            # Paged items
            rows = execute_query(
                f"""
                SELECT service, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                  {provider_where}
                GROUP BY service
                ORDER BY cost_usd DESC
                LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
                """,
                params,
            )
            cost_total = sum(r["cost_usd"] for r in rows) or 1
            items = [
                ServiceBreakdown(
                    service=r["service"],
                    cost_usd=r["cost_usd"],
                    percentage=round(r["cost_usd"] / cost_total * 100, 1),
                )
                for r in rows
            ]
            return items, total
        except Exception as e:
            log.warning("ledger.top_services.failed", error=str(e))
            return [], 0

    def get_top_teams(
        self,
        org_id: UUID,
        days: int = 30,
        limit: int = 10,
        offset: int = 0,
        provider: str | None = None,
    ) -> tuple[list[ServiceBreakdown], int]:
        end = date.today()
        start = end - timedelta(days=days)
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {
            "org_id": str(org_id),
            "start": start,
            "end": end,
            "limit": limit,
            "offset": offset,
        }
        if provider:
            params["provider"] = provider
        try:
            # Total count
            total_rows = execute_query(
                f"""
                SELECT count(DISTINCT owner_team) as total
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                  {provider_where}
                """,
                params,
            )
            total = int(total_rows[0]["total"]) if total_rows else 0

            # Paged items
            rows = execute_query(
                f"""
                SELECT owner_team as service, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                  {provider_where}
                GROUP BY owner_team
                ORDER BY cost_usd DESC
                LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
                """,
                params,
            )
            cost_total = sum(r["cost_usd"] for r in rows) or 1
            items = [
                ServiceBreakdown(
                    service=r["service"],
                    cost_usd=r["cost_usd"],
                    percentage=round(r["cost_usd"] / cost_total * 100, 1),
                )
                for r in rows
            ]
            return items, total
        except Exception as e:
            log.warning("ledger.top_teams.failed", error=str(e))
            return [], 0

    def get_month_cost(
        self,
        org_id: UUID,
        year: int,
        month: int,
        provider: str | None = None,
    ) -> float:
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {"org_id": str(org_id), "year": year, "month": month}
        if provider:
            params["provider"] = provider
        try:
            rows = execute_query(
                f"""
                SELECT sum(cost_usd) as total
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND toYear(date) = {{year:UInt16}}
                  AND toMonth(date) = {{month:UInt8}}
                  {provider_where}
                """,
                params,
            )
            return float(rows[0]["total"]) if rows else 0.0
        except Exception:
            return 0.0

    def get_event_count(self, org_id: UUID, days: int = 7, provider: str | None = None) -> int:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {"org_id": str(org_id), "start": start}
        if provider:
            params["provider"] = provider
        try:
            rows = execute_query(
                f"""
                SELECT count() as cnt
                FROM event_facts
                WHERE org_id = {{org_id:String}}
                  AND timestamp >= {{start:DateTime}}
                  {provider_where}
                """,
                params,
            )
            return int(rows[0]["cnt"]) if rows else 0
        except Exception:
            return 0

    async def get_dashboard_metrics(
        self,
        org_id: UUID,
        active_accounts: int,
        provider: str | None = None,
    ) -> DashboardMetrics:
        today = date.today()
        current_month = self.get_month_cost(org_id, today.year, today.month, provider=provider)
        prev_month = today.replace(day=1) - timedelta(days=1)
        previous_month = self.get_month_cost(
            org_id,
            prev_month.year,
            prev_month.month,
            provider=provider,
        )
        mom_change = (
            (current_month - previous_month) / previous_month * 100 if previous_month else 0
        )

        top_services, _ = self.get_top_services(org_id, provider=provider)
        top_teams, _ = self.get_top_teams(org_id, provider=provider)
        return DashboardMetrics(
            current_month_cost=current_month,
            previous_month_cost=previous_month,
            mom_change_pct=round(mom_change, 1),
            daily_trend=self.get_cost_trend(org_id, days=30, provider=provider),
            top_services=top_services,
            top_teams=top_teams,
            event_count_7d=self.get_event_count(org_id, days=7, provider=provider),
            active_accounts=active_accounts,
        )

    def get_reservation_coverage(
        self,
        org_id: UUID,
        days: int = 30,
        provider: str | None = None,
    ) -> ReservationCoverageSummary:
        end = date.today()
        start = end - timedelta(days=days)
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {"org_id": str(org_id), "start": start, "end": end}
        if provider:
            params["provider"] = provider

        # Heuristic detection:
        # - "compute" rows come from VM/compute services
        # - "reserved" rows are detected by service naming or tag values mentioning reservation/savings/commitment
        # This works across providers with different line-item schemas.
        base_query = f"""
            SELECT
                service,
                sum(
                    if(
                        positionCaseInsensitiveUTF8(service, 'virtual machine') > 0
                        OR positionCaseInsensitiveUTF8(service, 'compute') > 0
                        OR positionCaseInsensitiveUTF8(service, 'ec2') > 0
                        OR positionCaseInsensitiveUTF8(service, 'aks') > 0,
                        cost_usd,
                        0
                    )
                ) AS compute_cost_usd,
                sum(
                    if(
                        positionCaseInsensitiveUTF8(service, 'reservation') > 0
                        OR positionCaseInsensitiveUTF8(service, 'reserved') > 0
                        OR positionCaseInsensitiveUTF8(service, 'savings plan') > 0
                        OR positionCaseInsensitiveUTF8(service, 'commitment') > 0
                        OR arrayExists(
                            v -> (
                                positionCaseInsensitiveUTF8(v, 'reservation') > 0
                                OR positionCaseInsensitiveUTF8(v, 'reserved') > 0
                                OR positionCaseInsensitiveUTF8(v, 'savings') > 0
                                OR positionCaseInsensitiveUTF8(v, 'commitment') > 0
                            ),
                            mapValues(tags_map)
                        ),
                        cost_usd,
                        0
                    )
                ) AS reserved_cost_usd
            FROM cost_facts
            WHERE org_id = {{org_id:String}}
              AND date >= {{start:Date}}
              AND date <= {{end:Date}}
              {provider_where}
            GROUP BY service
            HAVING compute_cost_usd > 0 OR reserved_cost_usd > 0
            ORDER BY compute_cost_usd DESC
            LIMIT 50
        """

        try:
            rows = execute_query(
                base_query,
                params,
            )
        except Exception as exc:
            log.warning("ledger.reservation_coverage.failed", error=str(exc))
            rows = []

        services: list[ReservationCoverageByService] = []
        total_compute = 0.0
        total_reserved = 0.0

        for row in rows:
            compute_cost = float(row.get("compute_cost_usd") or 0.0)
            reserved_cost = float(row.get("reserved_cost_usd") or 0.0)
            uncovered = max(compute_cost - reserved_cost, 0.0)
            coverage = round(min((reserved_cost / compute_cost) * 100, 100.0), 1) if compute_cost > 0 else 0.0

            total_compute += compute_cost
            total_reserved += reserved_cost

            if compute_cost > 0:
                services.append(
                    ReservationCoverageByService(
                        service=str(row.get("service") or "unknown"),
                        compute_cost_usd=round(compute_cost, 2),
                        reserved_cost_usd=round(reserved_cost, 2),
                        uncovered_cost_usd=round(uncovered, 2),
                        coverage_pct=coverage,
                    )
                )

        uncovered_total = max(total_compute - total_reserved, 0.0)
        coverage_total = round(min((total_reserved / total_compute) * 100, 100.0), 1) if total_compute > 0 else 0.0
        has_active_reservations = total_reserved > 0

        if total_compute <= 0:
            recommendation = "Sem custo de compute no período para avaliar cobertura de reserva."
        elif not has_active_reservations:
            recommendation = "Nenhuma reserva detectada. Avalie compra de Reserved Instances/Savings Plans para reduzir custo."
        elif coverage_total < 60:
            recommendation = "Cobertura baixa de reservas. Priorize recursos de compute com maior custo descoberto."
        elif coverage_total < 85:
            recommendation = "Cobertura parcial. Ajuste mix de reserva para reduzir custo on-demand residual."
        else:
            recommendation = "Cobertura saudável de reservas no período analisado."

        return ReservationCoverageSummary(
            period_start=start,
            period_end=end,
            total_compute_cost_usd=round(total_compute, 2),
            total_reserved_cost_usd=round(total_reserved, 2),
            uncovered_compute_cost_usd=round(uncovered_total, 2),
            coverage_pct=coverage_total,
            has_active_reservations=has_active_reservations,
            services=services,
            recommendation=recommendation,
        )

    @staticmethod
    def _extract_family_token(raw_value: str) -> str | None:
        if not raw_value:
            return None

        value = raw_value.strip()
        if not value:
            return None

        # Common cloud SKU formats:
        # - Standard_B2s
        # - B2s
        # - m5.large
        # - t3.micro
        normalized = value.replace("Standard_", "").replace("standard_", "")
        direct_match = re.search(r"\b([A-Za-z]+\d+[A-Za-z0-9.]*)\b", normalized)
        if direct_match:
            return direct_match.group(1)

        dotted_match = re.search(r"\b([a-z]\d\.[a-z0-9]+)\b", normalized, flags=re.IGNORECASE)
        if dotted_match:
            return dotted_match.group(1)

        return None

    def _detect_reservation_family(
        self,
        service: str | None,
        resource_name: str | None,
        tags: dict | None,
    ) -> str:
        if isinstance(tags, dict):
            preferred_keys = (
                "family",
                "sku",
                "sku_name",
                "vm_size",
                "vmsize",
                "instance_type",
                "instancetype",
            )
            for key in preferred_keys:
                value = tags.get(key)
                if isinstance(value, str):
                    token = self._extract_family_token(value)
                    if token:
                        return token

            for value in tags.values():
                if isinstance(value, str):
                    token = self._extract_family_token(value)
                    if token:
                        return token

        for candidate in (resource_name or "", service or ""):
            token = self._extract_family_token(candidate)
            if token:
                return token

        return "unknown"

    @staticmethod
    def _recommend_efficiency_action(
        utilization_pct: float,
        reserved_cost_usd: float,
        compute_cost_usd: float,
        resource_count: int,
        *,
        exchange_hint: bool = False,
        renewal_window_days: int | None = None,
    ) -> tuple[str, str, float]:
        idle_cost = max(reserved_cost_usd - compute_cost_usd, 0.0)
        utilization_gap = max(100.0 - utilization_pct, 0.0)
        confidence = min(0.55 + (utilization_gap / 200.0), 0.95)

        if utilization_pct >= 85:
            return (
                "keep",
                "Reserva com boa aderencia de uso no periodo; manter estrategia atual.",
                0.9,
            )

        if renewal_window_days is not None and renewal_window_days <= 45 and utilization_pct < 50:
            return (
                "do_not_renew",
                "Reserva com renovacao proxima e baixa eficiencia; evitar renovacao sem replanejamento.",
                max(confidence, 0.87),
            )

        if exchange_hint and utilization_pct < 75:
            return (
                "exchange_reservation",
                "Advisor sinaliza oportunidade de troca e a utilizacao esta abaixo do ideal.",
                max(confidence, 0.84),
            )

        if utilization_pct < 25 and resource_count <= 1 and compute_cost_usd < (reserved_cost_usd * 0.40):
            return (
                "schedule_stop",
                "Reserva altamente ociosa com workload pequeno; avaliar desligamento/agendamento da VM.",
                max(confidence, 0.85),
            )

        if utilization_pct < 35 and resource_count == 0:
            return (
                "do_not_renew",
                "Reserva sem consumo detectado para a familia no periodo; evitar renovacao no proximo ciclo.",
                max(confidence, 0.88),
            )

        if utilization_pct < 60 and resource_count > 0:
            return (
                "exchange_reservation",
                "Cobertura baixa e mismatch de uso; avaliar exchange para familia/SKU mais aderente.",
                max(confidence, 0.8),
            )

        if idle_cost > 0 and resource_count <= 1:
            return (
                "resize_resource",
                "Existe ociosidade relevante na reserva; redimensionar recurso pode melhorar aproveitamento.",
                max(confidence, 0.72),
            )

        return (
            "do_not_renew",
            "Reserva com baixa eficiencia no periodo; reavaliar renovacao e estrategia de compromisso.",
            max(confidence, 0.7),
        )

    @staticmethod
    def _parse_renewal_window_days(text: str) -> int | None:
        if not text:
            return None

        patterns = (
            r"expire[s]?\s+in\s+(\d{1,3})\s+day",
            r"renov[a-z]*\s+in\s+(\d{1,3})\s+day",
            r"(\d{1,3})\s+day[s]?\s+(?:to|until)\s+(?:expire|renew)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _compute_action_priority(
        *,
        utilization_pct: float,
        waste_cost_usd: float,
        renewal_window_days: int | None,
        exchange_eligible: bool,
    ) -> int:
        priority = 1
        if utilization_pct < 70:
            priority += 1
        if utilization_pct < 50:
            priority += 1
        if waste_cost_usd >= 100:
            priority += 1
        if renewal_window_days is not None and renewal_window_days <= 45:
            priority += 1
        if exchange_eligible and utilization_pct < 80:
            priority += 1
        return max(1, min(priority, 5))

    def get_reservation_efficiency(
        self,
        org_id: UUID,
        days: int = 30,
        provider: str | None = None,
    ) -> ReservationEfficiencySummary:
        end = date.today()
        start = end - timedelta(days=days)
        provider_where = "AND provider = {provider:String}" if provider else ""
        params = {"org_id": str(org_id), "start": start, "end": end}
        if provider:
            params["provider"] = provider

        costs_query = f"""
            SELECT
                service,
                resource_name,
                tags,
                sum(
                    if(
                        positionCaseInsensitiveUTF8(service, 'virtual machine') > 0
                        OR positionCaseInsensitiveUTF8(service, 'compute') > 0
                        OR positionCaseInsensitiveUTF8(service, 'ec2') > 0
                        OR positionCaseInsensitiveUTF8(service, 'aks') > 0,
                        cost_usd,
                        0
                    )
                ) AS compute_cost_usd,
                sum(
                    if(
                        positionCaseInsensitiveUTF8(service, 'reservation') > 0
                        OR positionCaseInsensitiveUTF8(service, 'reserved') > 0
                        OR positionCaseInsensitiveUTF8(service, 'savings plan') > 0
                        OR positionCaseInsensitiveUTF8(service, 'commitment') > 0
                        OR arrayExists(
                            v -> (
                                positionCaseInsensitiveUTF8(v, 'reservation') > 0
                                OR positionCaseInsensitiveUTF8(v, 'reserved') > 0
                                OR positionCaseInsensitiveUTF8(v, 'savings') > 0
                                OR positionCaseInsensitiveUTF8(v, 'commitment') > 0
                            ),
                            mapValues(tags_map)
                        ),
                        cost_usd,
                        0
                    )
                ) AS reserved_cost_usd
            FROM cost_facts
            WHERE org_id = {{org_id:String}}
              AND date >= {{start:Date}}
              AND date <= {{end:Date}}
              {provider_where}
            GROUP BY service, resource_name, tags_map
            HAVING compute_cost_usd > 0 OR reserved_cost_usd > 0
            LIMIT 10000
        """

        inventory_query = """
            SELECT sku_name, count() AS resource_count
            FROM resource_inventory
            WHERE org_id = {org_id:String}
            GROUP BY sku_name
        """
        advisor_query = """
            SELECT
                short_description,
                recommendation_type_id,
                service,
                estimated_savings_usd
            FROM recommendation_facts
            WHERE org_id = {org_id:String}
              AND fetched_at >= {start_dt:DateTime}
              AND (
                positionCaseInsensitiveUTF8(category, 'cost') > 0
                OR positionCaseInsensitiveUTF8(short_description, 'reservation') > 0
                OR positionCaseInsensitiveUTF8(short_description, 'savings plan') > 0
              )
            LIMIT 10000
        """

        try:
            cost_rows = execute_query(
                costs_query,
                params,
            )
        except Exception as exc:
            log.warning("ledger.reservation_efficiency.costs_failed", error=str(exc))
            cost_rows = []

        try:
            inventory_rows = execute_query(
                inventory_query,
                {"org_id": str(org_id)},
            )
        except Exception as exc:
            log.warning("ledger.reservation_efficiency.inventory_failed", error=str(exc))
            inventory_rows = []

        try:
            advisor_rows = execute_query(
                advisor_query,
                {
                    "org_id": str(org_id),
                    "start_dt": datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
                },
            )
        except Exception as exc:
            log.warning("ledger.reservation_efficiency.advisor_failed", error=str(exc))
            advisor_rows = []

        resources_by_family: dict[str, int] = {}
        for row in inventory_rows:
            family = self._detect_reservation_family(None, row.get("sku_name"), None)
            resources_by_family[family] = resources_by_family.get(family, 0) + int(row.get("resource_count") or 0)

        advisor_by_family: dict[str, dict[str, object]] = {}
        for row in advisor_rows:
            description = str(row.get("short_description") or "")
            recommendation_type_id = str(row.get("recommendation_type_id") or "")
            service_name = str(row.get("service") or "")
            family = self._detect_reservation_family(service_name, description, None)
            if family not in advisor_by_family:
                advisor_by_family[family] = {
                    "exchange_eligible": False,
                    "renewal_window_days": None,
                    "signals": set(),
                }

            signal_bucket = advisor_by_family[family]
            signals = signal_bucket["signals"]
            if isinstance(signals, set):
                if description:
                    signals.add(description)
                if recommendation_type_id:
                    signals.add(f"type:{recommendation_type_id}")

            lower_blob = f"{description} {recommendation_type_id}".lower()
            if any(token in lower_blob for token in ("exchange", "swap", "migrate", "right-size", "rightsize")):
                signal_bucket["exchange_eligible"] = True

            renewal_days = self._parse_renewal_window_days(description)
            current_days = signal_bucket.get("renewal_window_days")
            if renewal_days is not None and (current_days is None or renewal_days < current_days):
                signal_bucket["renewal_window_days"] = renewal_days

        family_buckets: dict[str, dict[str, float]] = {}
        for row in cost_rows:
            family = self._detect_reservation_family(
                row.get("service"),
                row.get("resource_name"),
                row.get("tags"),
            )
            if family not in family_buckets:
                family_buckets[family] = {
                    "compute_cost_usd": 0.0,
                    "reserved_cost_usd": 0.0,
                }
            family_buckets[family]["compute_cost_usd"] += float(row.get("compute_cost_usd") or 0.0)
            family_buckets[family]["reserved_cost_usd"] += float(row.get("reserved_cost_usd") or 0.0)

        families: list[ReservationEfficiencyByFamily] = []
        total_reserved = 0.0
        total_used = 0.0
        total_idle = 0.0
        total_waste = 0.0
        total_payg_equivalent = 0.0

        for family, values in family_buckets.items():
            compute_cost = values["compute_cost_usd"]
            reserved_cost = values["reserved_cost_usd"]

            if reserved_cost <= 0:
                continue

            effective_used = min(compute_cost, reserved_cost)
            idle_reserved = max(reserved_cost - effective_used, 0.0)
            utilization_pct = (effective_used / reserved_cost) * 100 if reserved_cost > 0 else 0.0

            # Conservative proxy: reserved commitment usually lands below PAYG list price.
            estimated_discount_rate = 0.30
            payg_equivalent = max(compute_cost, effective_used / (1.0 - estimated_discount_rate))
            waste_cost = idle_reserved
            advisor_signal = advisor_by_family.get(family, {})
            exchange_eligible = bool(advisor_signal.get("exchange_eligible", False))
            renewal_window_days = advisor_signal.get("renewal_window_days")
            advisory_signals_raw = advisor_signal.get("signals")
            advisory_signals = []
            if isinstance(advisory_signals_raw, set):
                advisory_signals = sorted(
                    (str(item) for item in advisory_signals_raw if item),
                )[:5]

            resource_count = resources_by_family.get(family, 0)
            action, reason, confidence = self._recommend_efficiency_action(
                utilization_pct=utilization_pct,
                reserved_cost_usd=reserved_cost,
                compute_cost_usd=compute_cost,
                resource_count=resource_count,
                exchange_hint=exchange_eligible,
                renewal_window_days=renewal_window_days if isinstance(renewal_window_days, int) else None,
            )
            action_priority = self._compute_action_priority(
                utilization_pct=utilization_pct,
                waste_cost_usd=waste_cost,
                renewal_window_days=renewal_window_days if isinstance(renewal_window_days, int) else None,
                exchange_eligible=exchange_eligible,
            )

            families.append(
                ReservationEfficiencyByFamily(
                    family=family,
                    reserved_capacity_units=round(reserved_cost, 2),
                    effective_used_units=round(effective_used, 2),
                    idle_reserved_units=round(idle_reserved, 2),
                    utilization_pct=round(min(utilization_pct, 100.0), 1),
                    waste_cost_usd=round(waste_cost, 2),
                    payg_equivalent_cost_usd=round(payg_equivalent, 2),
                    exchange_candidate=action == "exchange_reservation",
                    recommended_action=action,
                    reason=reason,
                    confidence=round(confidence, 2),
                    action_priority=action_priority,
                    exchange_eligible=exchange_eligible,
                    renewal_window_days=renewal_window_days if isinstance(renewal_window_days, int) else None,
                    advisory_signals=advisory_signals,
                )
            )

            total_reserved += reserved_cost
            total_used += effective_used
            total_idle += idle_reserved
            total_waste += waste_cost
            total_payg_equivalent += payg_equivalent

        families.sort(
            key=lambda item: (item.action_priority, item.waste_cost_usd),
            reverse=True,
        )

        avg_utilization = (total_used / total_reserved) * 100 if total_reserved > 0 else 0.0
        top_action = families[0].recommended_action if families else None

        if not families:
            recommendation = "Nenhuma reserva ativa detectada no periodo para analise de eficiencia."
        elif avg_utilization >= 85:
            recommendation = "Eficiencia global de reservas saudavel. Mantenha a estrategia atual."
        elif top_action == "exchange_reservation":
            recommendation = "Priorize exchange de reservas com maior ociosidade para familias mais aderentes."
        elif top_action == "schedule_stop":
            recommendation = "Existem reservas com baixa utilizacao em workloads pequenos; avalie desligamento programado."
        elif top_action == "resize_resource":
            recommendation = "Ha oportunidade de ganho com redimensionamento de recursos para aumentar aderencia da reserva."
        else:
            recommendation = "Eficiencia abaixo do ideal. Reavalie renovacao e mix de reservas no proximo ciclo."

        return ReservationEfficiencySummary(
            period_start=start,
            period_end=end,
            total_families=len(families),
            total_reserved_capacity_units=round(total_reserved, 2),
            total_effective_used_units=round(total_used, 2),
            total_idle_reserved_units=round(total_idle, 2),
            avg_utilization_pct=round(min(avg_utilization, 100.0), 1),
            total_waste_cost_usd=round(total_waste, 2),
            total_payg_equivalent_cost_usd=round(total_payg_equivalent, 2),
            families=families,
            recommendation=recommendation,
        )
