from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query, insert_rows
from app.core.logging import get_logger
from app.domains.cloud_accounts.service import CloudAccountService
from app.domains.cloud_ledger.schemas import (
    CostRow,
    CostSummary,
    CostTrend,
    DashboardMetrics,
    IngestResult,
    ServiceBreakdown,
)

log = get_logger(__name__)


class CloudLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_account(
        self, org_id: UUID, account_id: UUID, start: date, end: date
    ) -> IngestResult:
        from app.domains.connectors.azure.client import AzureConnectorClient

        account_service = CloudAccountService(self.db)
        account = await account_service.get_account(org_id, account_id)
        if not account:
            return IngestResult(account_id=account_id, cost_records=0, event_records=0, status="error", message="Account not found")

        creds = await account_service.get_azure_credentials(account)
        client = AzureConnectorClient.from_account(account, creds)

        try:
            costs = await client.fetch_costs(account.external_id, start, end)
            events = await client.fetch_events(account.external_id, start, end)
        except Exception as e:
            log.error("ledger.ingest.failed", account_id=str(account_id), error=str(e))
            return IngestResult(account_id=account_id, cost_records=0, event_records=0, status="error", message=str(e))

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

        # Update last sync
        account.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()

        log.info("ledger.ingest.done", account_id=str(account_id), costs=len(costs), events=len(events))
        return IngestResult(
            account_id=account_id,
            cost_records=len(costs),
            event_records=len(events),
            status="ok",
        )

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

    def get_top_services(self, org_id: UUID, days: int = 30, limit: int = 10) -> list[ServiceBreakdown]:
        end = date.today()
        start = end - timedelta(days=days)
        try:
            rows = execute_query(
                """
                SELECT service, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                GROUP BY service
                ORDER BY cost_usd DESC
                LIMIT {limit:UInt32}
                """,
                {"org_id": str(org_id), "start": start, "end": end, "limit": limit},
            )
            total = sum(r["cost_usd"] for r in rows) or 1
            return [
                ServiceBreakdown(
                    service=r["service"],
                    cost_usd=r["cost_usd"],
                    percentage=round(r["cost_usd"] / total * 100, 1),
                )
                for r in rows
            ]
        except Exception as e:
            log.warning("ledger.top_services.failed", error=str(e))
            return []

    def get_top_teams(self, org_id: UUID, days: int = 30, limit: int = 10) -> list[ServiceBreakdown]:
        end = date.today()
        start = end - timedelta(days=days)
        try:
            rows = execute_query(
                """
                SELECT owner_team as service, sum(cost_usd) as cost_usd
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {start:Date}
                  AND date <= {end:Date}
                GROUP BY owner_team
                ORDER BY cost_usd DESC
                LIMIT {limit:UInt32}
                """,
                {"org_id": str(org_id), "start": start, "end": end, "limit": limit},
            )
            total = sum(r["cost_usd"] for r in rows) or 1
            return [
                ServiceBreakdown(
                    service=r["service"],
                    cost_usd=r["cost_usd"],
                    percentage=round(r["cost_usd"] / total * 100, 1),
                )
                for r in rows
            ]
        except Exception as e:
            log.warning("ledger.top_teams.failed", error=str(e))
            return []

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

        return DashboardMetrics(
            current_month_cost=current_month,
            previous_month_cost=previous_month,
            mom_change_pct=round(mom_change, 1),
            daily_trend=self.get_cost_trend(org_id, days=30),
            top_services=self.get_top_services(org_id),
            top_teams=self.get_top_teams(org_id),
            event_count_7d=self.get_event_count(org_id, days=7),
            active_accounts=active_accounts,
        )
