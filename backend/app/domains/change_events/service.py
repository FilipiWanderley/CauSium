from __future__ import annotations
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.change_events.models import ChangeEvent, ChangeEventType
from app.domains.change_events.schemas import ChangeEventCreate


class ChangeEventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, org_id: UUID, req: ChangeEventCreate) -> ChangeEvent:
        event = ChangeEvent(org_id=org_id, **req.model_dump())
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def list(
        self,
        org_id: UUID,
        event_type: Optional[ChangeEventType] = None,
        environment: Optional[str] = None,
        team: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ChangeEvent], int]:
        filters = [ChangeEvent.org_id == org_id]
        if event_type:
            filters.append(ChangeEvent.event_type == event_type)
        if environment:
            filters.append(ChangeEvent.environment == environment)
        if team:
            filters.append(ChangeEvent.owner_team == team)

        count_result = await self.db.execute(
            select(func.count()).select_from(ChangeEvent).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(ChangeEvent)
            .where(*filters)
            .order_by(ChangeEvent.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def get(self, org_id: UUID, event_id: UUID) -> Optional[ChangeEvent]:
        result = await self.db.execute(
            select(ChangeEvent).where(ChangeEvent.id == event_id, ChangeEvent.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def link_causal(
        self, org_id: UUID, event_id: UUID, cost_impact_usd: float, confidence: float
    ) -> Optional[ChangeEvent]:
        event = await self.get(org_id, event_id)
        if not event:
            return None
        event.cost_impact_usd = cost_impact_usd
        event.causal_confidence = confidence
        await self.db.flush()
        await self.db.refresh(event)
        return event
