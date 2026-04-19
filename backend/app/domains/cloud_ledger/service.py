from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query, insert_rows
from app.core.logging import get_logger
from app.domains.cloud_accounts.service import CloudAccountService
from app.domains.cloud_ledger.schemas import (
    CostRow,
    CostSummary,
    CostTrend,
    DashboardMetrics,
    DetailedCostRow,
    IngestResult,
    ReservationCoverageByService,
    ReservationCoverageSummary,
    ServiceBreakdown,
)

log = get_logger(__name__)


class CloudLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_account(
        self, org_id: UUID, account_id: UUID, start: date, end: date
    ) -> IngestResult:
        from app.domains.cloud_accounts.models import CloudProvider
        from app.domains.connectors.aws.client import AwsConnectorClient
        from app.domains.connectors.azure.client import AzureConnectorClient
        from app.domains.connectors.factory import get_connector_for_account
        from app.domains.cloud_accounts.models import AwsCurIngestionCheckpoint, BlobIngestionCheckpoint

        account_service = CloudAccountService(self.db)
        account = await account_service.get_account(org_id, account_id)
        if not account:
            return IngestResult(account_id=account_id, cost_records=0, event_records=0, status="error", message="Account not found")

        creds = await account_service.get_azure_credentials(account)
        if account.provider == CloudProvider.AWS:
            creds = await account_service.get_aws_credentials(account)
        if account.provider == CloudProvider.GCP:
            creds = await account_service.get_gcp_credentials(account)
        client = get_connector_for_account(account, creds)

        try:
            checkpoint_keys: set[str] | None = None
            aws_checkpoint_keys: set[str] | None = None
            if isinstance(client, AzureConnectorClient):
                checkpoint_keys = await self._get_blob_checkpoint_keys(account.id)
            if isinstance(client, AwsConnectorClient):
                aws_checkpoint_keys = await self._get_aws_cur_checkpoint_keys(account.id)

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

            events = await client.fetch_events(account.external_id, start, end)
        except Exception as e:
            log.error("ledger.ingest.failed", account_id=str(account_id), error=str(e))
            return IngestResult(account_id=account_id, cost_records=0, event_records=0, status="error", message=str(e))

        blob_checkpoints: list[dict[str, str]] = []
        aws_cur_checkpoints: list[dict[str, str]] = []
        if isinstance(client, AzureConnectorClient):
            blob_checkpoints = client.consume_last_blob_checkpoints()
        if isinstance(client, AwsConnectorClient):
            aws_cur_checkpoints = client.consume_last_cur_checkpoints()

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
            }
            for r in costs
        ]
        if cost_rows:
            try:
                insert_rows("cost_facts", cost_rows)
            except Exception as e:
                log.warning("ledger.clickhouse.cost_insert_failed", error=str(e))
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

        # Azure-specific: recommendations, inventory, usage metrics
        recommendation_count = 0
        inventory_count = 0
        usage_count = 0

        if isinstance(client, AzureConnectorClient):
            recommendation_count = await self._ingest_azure_recommendations(
                client, org_id, account_id, account.external_id
            )
            inventory_count = await self._ingest_azure_inventory(
                client, org_id, account_id, account.external_id
            )
            usage_count = await self._ingest_azure_usage_metrics(
                client, org_id, account_id, account.external_id, start, end
            )

        # Update last sync
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

    async def _ingest_azure_recommendations(
        self,
        client,
        org_id,
        account_id,
        subscription_id: str,
    ) -> int:
        try:
            recs = await client.fetch_recommendations(subscription_id)
        except Exception as exc:
            log.warning("ledger.azure_recommendations.fetch_failed", error=str(exc))
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

    async def _ingest_azure_inventory(
        self,
        client,
        org_id,
        account_id,
        subscription_id: str,
    ) -> int:
        try:
            resources = await client.fetch_inventory(subscription_id)
        except Exception as exc:
            log.warning("ledger.azure_inventory.fetch_failed", error=str(exc))
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

    async def _ingest_azure_usage_metrics(
        self,
        client,
        org_id,
        account_id,
        subscription_id: str,
        start,
        end,
    ) -> int:
        try:
            usage = await client.fetch_usage_metrics(subscription_id, start, end)
        except Exception as exc:
            log.warning("ledger.azure_usage.fetch_failed", error=str(exc))
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

    def get_cost_trend(self, org_id: UUID, days: int = 30) -> list[CostTrend]:
        end = date.today()
        start = end - timedelta(days=days)
        try:
            rows = execute_query(
                """
                SELECT date, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                GROUP BY date
                ORDER BY date
                """,
                {"org_id": str(org_id), "start": start, "end": end},
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

    def get_top_services(self, org_id: UUID, days: int = 30, limit: int = 10, offset: int = 0) -> tuple[list[ServiceBreakdown], int]:
        end = date.today()
        start = end - timedelta(days=days)
        try:
            # Total count
            total_rows = execute_query(
                """
                SELECT count(DISTINCT service) as total
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                """,
                {"org_id": str(org_id), "start": start, "end": end},
            )
            total = int(total_rows[0]["total"]) if total_rows else 0

            # Paged items
            rows = execute_query(
                """
                SELECT service, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                GROUP BY service
                ORDER BY cost_usd DESC
                LIMIT {limit:UInt32} OFFSET {offset:UInt32}
                """,
                {"org_id": str(org_id), "start": start, "end": end, "limit": limit, "offset": offset},
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

    def get_top_teams(self, org_id: UUID, days: int = 30, limit: int = 10, offset: int = 0) -> tuple[list[ServiceBreakdown], int]:
        end = date.today()
        start = end - timedelta(days=days)
        try:
            # Total count
            total_rows = execute_query(
                """
                SELECT count(DISTINCT owner_team) as total
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                """,
                {"org_id": str(org_id), "start": start, "end": end},
            )
            total = int(total_rows[0]["total"]) if total_rows else 0

            # Paged items
            rows = execute_query(
                """
                SELECT owner_team as service, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                GROUP BY owner_team
                ORDER BY cost_usd DESC
                LIMIT {limit:UInt32} OFFSET {offset:UInt32}
                """,
                {"org_id": str(org_id), "start": start, "end": end, "limit": limit, "offset": offset},
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

    def get_month_cost(self, org_id: UUID, year: int, month: int) -> float:
        try:
            rows = execute_query(
                """
                SELECT sum(cost_usd) as total
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND toYear(date) = {year:UInt16}
                  AND toMonth(date) = {month:UInt8}
                """,
                {"org_id": str(org_id), "year": year, "month": month},
            )
            return float(rows[0]["total"]) if rows else 0.0
        except Exception:
            return 0.0

    def get_event_count(self, org_id: UUID, days: int = 7) -> int:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        try:
            rows = execute_query(
                """
                SELECT count() as cnt
                FROM event_facts
                WHERE org_id = {org_id:String}
                  AND timestamp >= {start:DateTime}
                """,
                {"org_id": str(org_id), "start": start},
            )
            return int(rows[0]["cnt"]) if rows else 0
        except Exception:
            return 0

    async def get_dashboard_metrics(self, org_id: UUID, active_accounts: int) -> DashboardMetrics:
        today = date.today()
        current_month = self.get_month_cost(org_id, today.year, today.month)
        prev_month = today.replace(day=1) - timedelta(days=1)
        previous_month = self.get_month_cost(org_id, prev_month.year, prev_month.month)
        mom_change = (
            (current_month - previous_month) / previous_month * 100 if previous_month else 0
        )

        top_services, _ = self.get_top_services(org_id)
        top_teams, _ = self.get_top_teams(org_id)
        return DashboardMetrics(
            current_month_cost=current_month,
            previous_month_cost=previous_month,
            mom_change_pct=round(mom_change, 1),
            daily_trend=self.get_cost_trend(org_id, days=30),
            top_services=top_services,
            top_teams=top_teams,
            event_count_7d=self.get_event_count(org_id, days=7),
            active_accounts=active_accounts,
        )

    def get_reservation_coverage(self, org_id: UUID, days: int = 30) -> ReservationCoverageSummary:
        end = date.today()
        start = end - timedelta(days=days)

        # Heuristic detection:
        # - "compute" rows come from VM/compute services
        # - "reserved" rows are detected by service naming or tag values mentioning reservation/savings/commitment
        # This works across providers with different line-item schemas.
        base_query = """
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
                            mapValues(tags)
                        ),
                        cost_usd,
                        0
                    )
                ) AS reserved_cost_usd
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {start:Date}
              AND date <= {end:Date}
            GROUP BY service
            HAVING compute_cost_usd > 0 OR reserved_cost_usd > 0
            ORDER BY compute_cost_usd DESC
            LIMIT 50
        """

        try:
            rows = execute_query(
                base_query,
                {"org_id": str(org_id), "start": start, "end": end},
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
