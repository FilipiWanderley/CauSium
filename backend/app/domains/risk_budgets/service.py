from __future__ import annotations
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.domains.audit_chain.service import AuditChainService
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService
from app.domains.risk_budgets.models import RiskBudget
from app.domains.risk_budgets.schemas import RiskBudgetCreate, RiskBudgetUpdate


class RiskBudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    async def create(
        self, org_id: UUID, req: RiskBudgetCreate, actor_user_id: UUID | None = None
    ) -> RiskBudget:
        budget = RiskBudget(org_id=org_id, **req.model_dump())
        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)

        notif = NotificationsService(self.db)
        await notif.create_if_rule_matches(
            org_id=org_id,
            category=AlertCategory.GOVERNANCE,
            severity=AlertSeverity.CRITICAL,
            event_type="risk_budget.created",
            title=f"Risk budget configured: {budget.domain} / {budget.environment}",
            body=f"Limit {budget.budget_type.value} set to {budget.limit_value}.",
            source_type="risk_budget",
            source_id=str(budget.id),
            extra_metadata={
                "domain": budget.domain,
                "environment": budget.environment,
                "budget_type": budget.budget_type.value,
            },
        )

        if actor_user_id:
            await self.audit_chain.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type="risk_budget.created",
                entity_type="risk_budget",
                entity_id=str(budget.id),
                payload={
                    "domain": budget.domain,
                    "environment": budget.environment,
                    "budget_type": budget.budget_type.value,
                    "limit_value": budget.limit_value,
                },
            )
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

    async def update(
        self, org_id: UUID, budget_id: UUID, req: RiskBudgetUpdate, actor_user_id: UUID | None = None
    ) -> RiskBudget | None:
        budget = await self.get(org_id, budget_id)
        if not budget:
            return None
        changes = req.model_dump(exclude_none=True)
        for field, value in changes.items():
            setattr(budget, field, value)
        await self.db.flush()
        await self.db.refresh(budget)
        if actor_user_id:
            await self.audit_chain.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type="risk_budget.updated",
                entity_type="risk_budget",
                entity_id=str(budget_id),
                payload=changes,
            )
        return budget

    async def delete(
        self, org_id: UUID, budget_id: UUID, actor_user_id: UUID | None = None
    ) -> bool:
        budget = await self.get(org_id, budget_id)
        if not budget:
            return False
        if actor_user_id:
            await self.audit_chain.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type="risk_budget.deleted",
                entity_type="risk_budget",
                entity_id=str(budget_id),
                payload={
                    "domain": budget.domain,
                    "environment": budget.environment,
                    "budget_type": budget.budget_type.value,
                    "limit_value": budget.limit_value,
                },
            )
        await self.db.delete(budget)
        return True
