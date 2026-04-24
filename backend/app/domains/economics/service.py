from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.logging import get_logger
from app.domains.economics.models import (
    FinancialBudgetPeriod,
    ReportExportJob,
    ReportExportStatus,
    WorkspaceBudget,
)
from app.domains.economics.schemas import ReportExportCreate, ReportExportJobOut, WorkspaceBudgetOut, WorkspaceBudgetUpsert
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService

log = get_logger(__name__)


def _period_window(period: FinancialBudgetPeriod) -> tuple[date, date, int]:
    """Return (period_start, today, days_in_period) for the *current* period.

    Returns
    -------
    period_start   First day of the current period (month / quarter / year).
    today          Date.today().
    days_total     Total calendar days in the full period.
    """
    today = date.today()

    if period == FinancialBudgetPeriod.MONTHLY:
        start = today.replace(day=1)
        days_total = calendar.monthrange(today.year, today.month)[1]

    elif period == FinancialBudgetPeriod.QUARTERLY:
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=q_start_month, day=1)
        # end of quarter = last day of (q_start_month + 2)
        q_end_month = q_start_month + 2
        days_total = (
            date(today.year, q_end_month, calendar.monthrange(today.year, q_end_month)[1])
            - start
        ).days + 1

    else:  # ANNUAL
        start = today.replace(month=1, day=1)
        days_total = 366 if calendar.isleap(today.year) else 365

    return start, today, days_total


def _query_cost(org_id: UUID, start: date, end: date) -> float:
    """Sum cost_usd from ClickHouse for [start, end] inclusive.  Returns 0.0 on failure."""
    try:
        rows = execute_query(
            """
            SELECT sum(cost_usd) AS total
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {start:Date}
              AND date <= {end:Date}
            """,
            {"org_id": str(org_id), "start": start, "end": end},
        )
        return float(rows[0]["total"]) if rows and rows[0]["total"] is not None else 0.0
    except Exception as exc:
        log.warning("economics.query_cost.failed", org_id=str(org_id), error=str(exc))
        return 0.0


class EconomicsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_budget(self, org_id: UUID) -> Optional[WorkspaceBudget]:
        result = await self.db.execute(
            select(WorkspaceBudget).where(WorkspaceBudget.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_budget_with_consumption(self, org_id: UUID) -> Optional[WorkspaceBudgetOut]:
        """Fetch the budget record and enrich it with live ClickHouse consumption data."""
        budget = await self.get_budget(org_id)
        if budget is None:
            return None

        period_start, today, days_total = _period_window(budget.period)
        consumed_usd = _query_cost(org_id, period_start, today)

        consumed_pct = (consumed_usd / budget.amount_usd * 100) if budget.amount_usd else 0.0

        # Linear day-rate projection to end-of-period
        days_elapsed = (today - period_start).days + 1  # inclusive
        if days_elapsed > 0 and consumed_usd > 0:
            projected_eom_usd = (consumed_usd / days_elapsed) * days_total
        else:
            projected_eom_usd = None

        out = WorkspaceBudgetOut.model_validate(budget)
        out.consumed_usd = round(consumed_usd, 2)
        out.consumed_pct = round(min(consumed_pct, 100.0), 1)
        out.projected_eom_usd = round(projected_eom_usd, 2) if projected_eom_usd is not None else None

        try:
            thresholds = sorted(json.loads(budget.alert_thresholds))
        except Exception:
            thresholds = []

        crossed = [t for t in thresholds if consumed_pct >= float(t)]
        if crossed:
            highest = int(max(crossed))
            notif = NotificationsService(self.db)
            await notif.create_realtime_alert(
                org_id=org_id,
                category=AlertCategory.FINANCIAL,
                severity=AlertSeverity.CRITICAL,
                event_type="budget.threshold.crossed",
                title=f"Budget threshold reached: {highest}%",
                body=(
                    f"Workspace consumed {round(consumed_pct, 1)}% of budget "
                    f"for current {budget.period.value} period."
                ),
                source_type="workspace_budget",
                source_id=f"{budget.id}:{period_start.isoformat()}:{highest}",
                extra_metadata={
                    "threshold": highest,
                    "consumed_pct": round(consumed_pct, 1),
                    "period": budget.period.value,
                },
            )
        return out

    async def get_report_export_job(self, org_id: UUID, job_id: UUID) -> Optional[ReportExportJob]:
        result = await self.db.execute(
            select(ReportExportJob).where(
                ReportExportJob.id == job_id,
                ReportExportJob.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def serialize_report_export_job(job: ReportExportJob) -> ReportExportJobOut:
        return ReportExportJobOut(
            id=job.id,
            org_id=job.org_id,
            requested_by_user_id=job.requested_by_user_id,
            report_type=job.report_type,
            file_format=job.file_format,
            status=job.status,
            window_days=job.window_days,
            filters=job.filters,
            file_name=job.file_name,
            content_type=job.content_type,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            expires_at=job.expires_at,
            download_ready=bool(job.storage_path and job.status == ReportExportStatus.COMPLETED),
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert_budget(self, org_id: UUID, req: WorkspaceBudgetUpsert) -> WorkspaceBudgetOut:
        """Insert or update the workspace budget (one per org)."""
        budget = await self.get_budget(org_id)

        if budget is None:
            budget = WorkspaceBudget(
                org_id=org_id,
                amount_usd=req.amount_usd,
                period=req.period,
                currency=req.currency.upper(),
                alert_thresholds=json.dumps(req.alert_thresholds),
            )
            self.db.add(budget)
        else:
            budget.amount_usd = req.amount_usd
            budget.period = req.period
            budget.currency = req.currency.upper()
            budget.alert_thresholds = json.dumps(req.alert_thresholds)

        await self.db.flush()
        await self.db.refresh(budget)

        # Return with up-to-date consumption metrics
        result = await self.get_budget_with_consumption(org_id)
        # Should never be None right after an upsert, but guard gracefully
        return result or WorkspaceBudgetOut.model_validate(budget)

    async def create_report_export_job(
        self,
        org_id: UUID,
        requested_by_user_id: UUID,
        req: ReportExportCreate,
    ) -> ReportExportJobOut:
        """Persist an export job in queued state.

        Phase 1 intentionally stops at job creation so the API contract, audit trail,
        and workspace scoping exist before the async worker is introduced.
        """
        job = ReportExportJob(
            org_id=org_id,
            requested_by_user_id=requested_by_user_id,
            report_type=req.report_type,
            file_format=req.file_format,
            window_days=req.window_days,
            filters=req.filters,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        log.info(
            "economics.report_export.queued",
            org_id=str(org_id),
            export_job_id=str(job.id),
            requested_by_user_id=str(requested_by_user_id),
            report_type=job.report_type.value,
            file_format=job.file_format.value,
        )
        return self.serialize_report_export_job(job)

    async def mark_report_export_running(self, job: ReportExportJob) -> ReportExportJob:
        job.status = ReportExportStatus.RUNNING
        if job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        job.error_message = None
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def mark_report_export_completed(
        self,
        job: ReportExportJob,
        *,
        file_name: str,
        storage_path: str,
        content_type: str,
        expires_at: datetime,
    ) -> ReportExportJob:
        job.status = ReportExportStatus.COMPLETED
        job.file_name = file_name
        job.storage_path = storage_path
        job.content_type = content_type
        job.error_message = None
        if job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        job.completed_at = datetime.now(timezone.utc)
        job.expires_at = expires_at
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def mark_report_export_failed(
        self,
        job: ReportExportJob,
        error_message: str,
    ) -> ReportExportJob:
        job.status = ReportExportStatus.FAILED
        job.error_message = error_message[:2000]
        if job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        job.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job)
        return job
