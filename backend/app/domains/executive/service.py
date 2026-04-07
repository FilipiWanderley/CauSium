from __future__ import annotations
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.logging import get_logger
from app.domains.decision_engine.models import OptimizationOpportunity, OpportunityStatus
from app.domains.executive.schemas import (
    ExecutiveSummary,
    SavingsRecord,
    ScorecardResponse,
    TeamScorecard,
)
from app.domains.workflow.models import Initiative, InitiativeStatus

log = get_logger(__name__)


class ExecutiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_month_cost(self, org_id: UUID, year: int, month: int) -> float:
        try:
            rows = execute_query(
                "SELECT sum(cost_usd) as total FROM cost_facts WHERE org_id={org:String} AND toYear(date)={y:UInt16} AND toMonth(date)={m:UInt8}",
                {"org": str(org_id), "y": year, "m": month},
            )
            return float(rows[0]["total"]) if rows else 0.0
        except Exception:
            return 0.0

    def _get_ytd_cost(self, org_id: UUID, year: int) -> float:
        try:
            rows = execute_query(
                "SELECT sum(cost_usd) as total FROM cost_facts WHERE org_id={org:String} AND toYear(date)={y:UInt16}",
                {"org": str(org_id), "y": year},
            )
            return float(rows[0]["total"]) if rows else 0.0
        except Exception:
            return 0.0

    def _simple_forecast(self, org_id: UUID) -> tuple[float, str]:
        """Linear forecast based on last 3 months average."""
        today = date.today()
        monthly_costs = []
        for i in range(1, 4):
            d = (today.replace(day=1) - timedelta(days=i * 28))
            monthly_costs.append(self._get_month_cost(org_id, d.year, d.month))

        if not any(monthly_costs):
            return 0.0, "insufficient_data"

        avg = sum(monthly_costs) / len([c for c in monthly_costs if c > 0])
        return round(avg * 1.05, 2), "low"  # 5% growth assumption

    async def get_summary(self, org_id: UUID) -> ExecutiveSummary:
        today = date.today()
        prev = (today.replace(day=1) - timedelta(days=1))

        current_cost = self._get_month_cost(org_id, today.year, today.month)
        prev_cost = self._get_month_cost(org_id, prev.year, prev.month)
        mom = (current_cost - prev_cost) / prev_cost * 100 if prev_cost else 0
        ytd = self._get_ytd_cost(org_id, today.year)
        forecast, confidence = self._simple_forecast(org_id)

        # Savings from completed initiatives
        result = await self.db.execute(
            select(
                func.sum(Initiative.realized_savings_usd).label("total"),
            ).where(
                Initiative.org_id == org_id,
                Initiative.status == InitiativeStatus.DONE,
                Initiative.realized_savings_usd.isnot(None),
            )
        )
        total_realized = float(result.scalar() or 0)

        # Savings this month
        result2 = await self.db.execute(
            select(func.sum(Initiative.realized_savings_usd)).where(
                Initiative.org_id == org_id,
                Initiative.status == InitiativeStatus.DONE,
                Initiative.realized_savings_usd.isnot(None),
                func.date_trunc("month", Initiative.completed_at) == func.date_trunc("month", func.now()),
            )
        )
        savings_this_month = float(result2.scalar() or 0)

        # Total potential from open opportunities
        result3 = await self.db.execute(
            select(func.sum(OptimizationOpportunity.estimated_monthly_savings_usd)).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == OpportunityStatus.OPEN,
            )
        )
        total_potential = float(result3.scalar() or 0)

        open_opps = await self.db.scalar(
            select(func.count()).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == OpportunityStatus.OPEN,
            )
        ) or 0

        in_progress = await self.db.scalar(
            select(func.count()).where(
                Initiative.org_id == org_id,
                Initiative.status == InitiativeStatus.IN_PROGRESS,
            )
        ) or 0

        completed = await self.db.scalar(
            select(func.count()).where(
                Initiative.org_id == org_id,
                Initiative.status == InitiativeStatus.DONE,
            )
        ) or 0

        # Top savings
        top_result = await self.db.execute(
            select(Initiative).where(
                Initiative.org_id == org_id,
                Initiative.status == InitiativeStatus.DONE,
                Initiative.realized_savings_usd.isnot(None),
            ).order_by(Initiative.realized_savings_usd.desc()).limit(5)
        )
        top_savings = [
            SavingsRecord(
                initiative_id=i.id,
                title=i.title,
                realized_savings_usd=i.realized_savings_usd,
                completed_at=i.completed_at.isoformat() if i.completed_at else None,
            )
            for i in top_result.scalars().all()
        ]

        return ExecutiveSummary(
            current_month_cost_usd=current_cost,
            previous_month_cost_usd=prev_cost,
            mom_change_pct=round(mom, 1),
            ytd_cost_usd=ytd,
            total_realized_savings_usd=total_realized,
            total_potential_savings_usd=total_potential,
            savings_this_month_usd=savings_this_month,
            open_opportunities=open_opps,
            in_progress_initiatives=in_progress,
            completed_initiatives=completed,
            forecast_next_month_usd=forecast,
            forecast_confidence=confidence,
            top_savings=top_savings,
        )

    async def get_scorecard(self, org_id: UUID) -> ScorecardResponse:
        today = date.today()
        prev = (today.replace(day=1) - timedelta(days=1))

        try:
            current_rows = execute_query(
                "SELECT owner_team, sum(cost_usd) as cost FROM cost_facts WHERE org_id={org:String} AND toYear(date)={y:UInt16} AND toMonth(date)={m:UInt8} GROUP BY owner_team",
                {"org": str(org_id), "y": today.year, "m": today.month},
            )
            prev_rows = execute_query(
                "SELECT owner_team, sum(cost_usd) as cost FROM cost_facts WHERE org_id={org:String} AND toYear(date)={y:UInt16} AND toMonth(date)={m:UInt8} GROUP BY owner_team",
                {"org": str(org_id), "y": prev.year, "m": prev.month},
            )
        except Exception:
            current_rows, prev_rows = [], []

        current_by_team = {r["owner_team"]: float(r["cost"]) for r in current_rows}
        prev_by_team = {r["owner_team"]: float(r["cost"]) for r in prev_rows}
        all_teams = set(current_by_team) | set(prev_by_team)

        scorecards = []
        for team in all_teams:
            curr = current_by_team.get(team, 0)
            prev_c = prev_by_team.get(team, 0)
            mom = (curr - prev_c) / prev_c * 100 if prev_c else 0

            open_opps = await self.db.scalar(
                select(func.count()).where(
                    OptimizationOpportunity.org_id == org_id,
                    OptimizationOpportunity.owner_team == team,
                    OptimizationOpportunity.status == OpportunityStatus.OPEN,
                )
            ) or 0

            savings_result = await self.db.execute(
                select(func.sum(Initiative.realized_savings_usd)).where(
                    Initiative.org_id == org_id,
                    Initiative.status == InitiativeStatus.DONE,
                )
            )
            realized = float(savings_result.scalar() or 0)

            # Efficiency score: penalize cost growth, reward savings
            eff = max(0.0, min(100.0, 70 - mom * 2 + (realized / max(curr, 1)) * 30))

            scorecards.append(TeamScorecard(
                team=team,
                current_month_cost_usd=curr,
                previous_month_cost_usd=prev_c,
                mom_change_pct=round(mom, 1),
                open_opportunities=open_opps,
                realized_savings_usd=realized,
                efficiency_score=round(eff, 1),
            ))

        scorecards.sort(key=lambda x: x.efficiency_score, reverse=True)
        org_score = sum(s.efficiency_score for s in scorecards) / len(scorecards) if scorecards else 0

        return ScorecardResponse(teams=scorecards, org_efficiency_score=round(org_score, 1))
