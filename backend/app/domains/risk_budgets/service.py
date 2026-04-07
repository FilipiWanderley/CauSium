from __future__ import annotations
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.risk_budgets.models import RiskBudget
from app.domains.risk_budgets.schemas import RiskBudgetCreate, RiskBudgetUpdate


class RiskBudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, org_id: UUID, req: RiskBudgetCreate) -> RiskBudget:
        budget = RiskBudget(org_id=org_id, **req.model_dump())
        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)
        return budget

    async def list(
        self, org_id: UUID, active_only: bool = False, limit: int = 100, offset: int = 0
    ) -> tuple[list[RiskBudget], int]:
        filters = [RiskBudget.org_id == org_id]
        if active_only:
            filters.append(RiskBudget.is_active.is_(True))

        count_result = await self.db.execute(
            select(func.count()).select_from(RiskBudget).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(RiskBudget)
            .where(*filters)
            .order_by(RiskBudget.domain, RiskBudget.environment)
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def get(self, org_id: UUID, budget_id: UUID) -> Optional[RiskBudget]:
        result = await self.db.execute(
            select(RiskBudget).where(RiskBudget.id == budget_id, RiskBudget.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def update(self, org_id: UUID, budget_id: UUID, req: RiskBudgetUpdate) -> Optional[RiskBudget]:
        budget = await self.get(org_id, budget_id)
        if not budget:
            return None
        for field, value in req.model_dump(exclude_none=True).items():
            setattr(budget, field, value)
        await self.db.flush()
        await self.db.refresh(budget)
        return budget

    async def delete(self, org_id: UUID, budget_id: UUID) -> bool:
        budget = await self.get(org_id, budget_id)
        if not budget:
            return False
        await self.db.delete(budget)
        return True
