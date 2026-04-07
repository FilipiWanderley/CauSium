from __future__ import annotations

import calendar
import json
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.logging import get_logger
from app.domains.economics.models import FinancialBudgetPeriod, WorkspaceBudget
from app.domains.economics.schemas import WorkspaceBudgetOut, WorkspaceBudgetUpsert

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
        return out

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
