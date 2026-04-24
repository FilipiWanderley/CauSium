from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.logging import get_logger
from app.domains.auth.models import Organization, WorkspaceLifecycleState
from app.domains.cloud_accounts.models import CloudAccount, ConnectorStatus
from app.domains.intel.models import UsageObservation

log = get_logger(__name__)

_METRICS = (
    "Percentage CPU",
    "CPUUtilization",
    # Memory metrics can come from guest/insights depending on provider setup.
    "Memory Percentage",
    "MemoryUtilization",
    "Available Memory Bytes",
    "Available Memory",
    "Memory Available Bytes",
    "AvailableMemoryBytes",
    "Network In Total",
    "Network Out Total",
    "NetworkIn",
    "NetworkOut",
    "Disk Read Bytes",
    "Disk Write Bytes",
    "DiskReadBytes",
    "DiskWriteBytes",
    # AKS/Kubernetes node-pool capacity signals (Sprint 2 data integration).
    "Node Count",
    "NodeCount",
    "Allocated CPU",
    "Allocated Memory",
    "Requested CPU",
    "Requested Memory",
)


@dataclass(frozen=True)
class UsageObservationRunResult:
    scanned_accounts: int
    created_rows: int
    deleted_rows: int


class UsageObservationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ingest_recent_usage_observations(self, *, window_hours: int = 3) -> UsageObservationRunResult:
        now_utc = datetime.now(timezone.utc)
        window_end = now_utc.replace(minute=0, second=0, microsecond=0)
        window_start = window_end - timedelta(hours=max(1, window_hours))

        accounts = await self._list_active_accounts()
        if not accounts:
            return UsageObservationRunResult(scanned_accounts=0, created_rows=0, deleted_rows=0)

        created_rows = 0
        deleted_rows = 0
        for account in accounts:
            stats = self._fetch_usage_stats(
                org_id=str(account.org_id),
                account_id=str(account.id),
                window_start=window_start,
                window_end=window_end,
            )
            if not stats:
                continue

            delete_stmt = (
                delete(UsageObservation)
                .where(UsageObservation.org_id == account.org_id)
                .where(UsageObservation.account_id == account.id)
                .where(UsageObservation.window_start == window_start)
                .where(UsageObservation.window_end == window_end)
            )
            delete_result = await self.db.execute(delete_stmt)
            deleted_rows += int(delete_result.rowcount or 0)

            for row in stats:
                self.db.add(
                    UsageObservation(
                        org_id=account.org_id,
                        account_id=account.id,
                        provider=str(row.get("provider") or "unknown"),
                        resource_id=str(row.get("resource_id") or ""),
                        metric_name=str(row.get("metric_name") or ""),
                        window_start=window_start,
                        window_end=window_end,
                        avg_value=float(row.get("avg_value") or 0.0),
                        p95_value=float(row.get("p95_value") or 0.0),
                        max_value=float(row.get("max_value") or 0.0),
                        min_value=float(row.get("min_value") or 0.0),
                        sample_count=int(row.get("sample_count") or 0),
                        unit=(str(row.get("metric_unit")) if row.get("metric_unit") else None),
                        region=(str(row.get("region")) if row.get("region") else None),
                        environment=(str(row.get("environment")) if row.get("environment") else None),
                    )
                )
            created_rows += len(stats)

        await self.db.flush()
        return UsageObservationRunResult(
            scanned_accounts=len(accounts),
            created_rows=created_rows,
            deleted_rows=deleted_rows,
        )

    async def _list_active_accounts(self) -> list[CloudAccount]:
        result = await self.db.execute(
            select(CloudAccount)
            .join(Organization, Organization.id == CloudAccount.org_id)
            .where(
                Organization.is_active.is_(True),
                Organization.lifecycle_state == WorkspaceLifecycleState.ACTIVE,
                CloudAccount.status.in_([ConnectorStatus.ACTIVE, ConnectorStatus.ERROR]),
            )
        )
        return list(result.scalars().all())

    def _fetch_usage_stats(
        self,
        *,
        org_id: str,
        account_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[dict[str, Any]]:
        try:
            rows = execute_query(
                """
                SELECT
                  provider,
                  resource_id,
                  metric_name,
                  anyLast(metric_unit) AS metric_unit,
                  anyLast(region) AS region,
                  anyLast(environment) AS environment,
                  avg(metric_value) AS avg_value,
                  quantileExact(0.95)(metric_value) AS p95_value,
                  max(metric_value) AS max_value,
                  min(metric_value) AS min_value,
                  count() AS sample_count
                FROM usage_facts
                WHERE org_id = {org_id:String}
                  AND account_id = {account_id:String}
                  AND date >= {start_date:Date}
                  AND date <= {end_date:Date}
                  AND metric_name IN {metric_names:Array(String)}
                GROUP BY provider, resource_id, metric_name
                HAVING sample_count > 0 AND resource_id != ''
                """,
                {
                    "org_id": org_id,
                    "account_id": account_id,
                    "start_date": window_start.date(),
                    "end_date": window_end.date(),
                    "metric_names": list(_METRICS),
                },
            )
            return list(rows or [])
        except Exception as exc:
            log.warning(
                "intel.usage_observations.fetch_failed",
                org_id=org_id,
                account_id=account_id,
                reason=str(exc),
            )
            return []
