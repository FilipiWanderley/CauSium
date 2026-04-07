from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.audit_chain.service import AuditChainService
from app.domains.workflow.models import (
    Initiative,
    InitiativeComment,
    InitiativeStatus,
    VALID_TRANSITIONS,
)
from app.domains.workflow.schemas import (
    CommentCreate,
    InitiativeBoard,
    InitiativeCreate,
    InitiativeOut,
    InitiativeStatusTransition,
    InitiativeUpdate,
)

log = get_logger(__name__)


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    async def create_initiative(
        self, org_id: UUID, req: InitiativeCreate, actor_user_id: UUID | None = None
    ) -> Initiative:
        initiative = Initiative(
            org_id=org_id,
            opportunity_id=req.opportunity_id,
            owner_id=req.owner_id,
            title=req.title,
            description=req.description,
            sla_date=req.sla_date,
            external_ref=req.external_ref,
            external_url=req.external_url,
        )
        self.db.add(initiative)
        await self.db.flush()
        await self.db.refresh(initiative)

        # Update linked opportunity status
        if req.opportunity_id:
            from app.domains.decision_engine.models import OptimizationOpportunity, OpportunityStatus
            result = await self.db.execute(
                select(OptimizationOpportunity).where(OptimizationOpportunity.id == req.opportunity_id)
            )
            opp = result.scalar_one_or_none()
            if opp and opp.status == OpportunityStatus.OPEN:
                opp.status = OpportunityStatus.IN_PROGRESS

        if actor_user_id:
            await self.audit_chain.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type="initiative.created",
                entity_type="initiative",
                entity_id=str(initiative.id),
                payload={
                    "title": initiative.title,
                    "opportunity_id": str(req.opportunity_id) if req.opportunity_id else None,
                    "owner_id": str(req.owner_id) if req.owner_id else None,
                },
            )
        log.info("initiative.created", initiative_id=str(initiative.id), org_id=str(org_id))
        return initiative

    async def list_initiatives(
        self,
        org_id: UUID,
        status: InitiativeStatus | None = None,
        owner_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Initiative], int]:
        filters = [Initiative.org_id == org_id]
        if status:
            filters.append(Initiative.status == status)
        if owner_id:
            filters.append(Initiative.owner_id == owner_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(Initiative).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(Initiative)
            .where(*filters)
            .order_by(Initiative.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def get_initiative(self, org_id: UUID, initiative_id: UUID) -> Initiative | None:
        result = await self.db.execute(
            select(Initiative).where(
                Initiative.id == initiative_id,
                Initiative.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_initiative(
        self, org_id: UUID, initiative_id: UUID, req: InitiativeUpdate
    ) -> Initiative | None:
        initiative = await self.get_initiative(org_id, initiative_id)
        if not initiative:
            return None
        for field, value in req.model_dump(exclude_none=True).items():
            setattr(initiative, field, value)
        await self.db.flush()
        await self.db.refresh(initiative)
        return initiative

    async def transition_status(
        self, org_id: UUID, initiative_id: UUID, req: InitiativeStatusTransition,
        actor_user_id: UUID | None = None,
    ) -> Initiative:
        initiative = await self.get_initiative(org_id, initiative_id)
        if not initiative:
            raise ValueError("Initiative not found")

        allowed = VALID_TRANSITIONS.get(initiative.status, [])
        if req.status not in allowed:
            raise ValueError(
                f"Cannot transition from {initiative.status.value} to {req.status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        prev_status = initiative.status.value
        initiative.status = req.status
        if req.status == InitiativeStatus.DONE:
            initiative.completed_at = datetime.now(timezone.utc)
            # Mark linked opportunity as resolved
            if initiative.opportunity_id:
                from app.domains.decision_engine.models import OptimizationOpportunity, OpportunityStatus
                result = await self.db.execute(
                    select(OptimizationOpportunity).where(
                        OptimizationOpportunity.id == initiative.opportunity_id
                    )
                )
                opp = result.scalar_one_or_none()
                if opp:
                    opp.status = OpportunityStatus.RESOLVED

        await self.db.flush()
        await self.db.refresh(initiative)

        if actor_user_id:
            await self.audit_chain.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type="initiative.transitioned",
                entity_type="initiative",
                entity_id=str(initiative_id),
                payload={"from": prev_status, "to": req.status.value},
            )
        log.info("initiative.transitioned", initiative_id=str(initiative_id), new_status=req.status.value)
        return initiative

    async def add_comment(
        self, org_id: UUID, initiative_id: UUID, user_id: UUID, req: CommentCreate
    ) -> InitiativeComment:
        initiative = await self.get_initiative(org_id, initiative_id)
        if not initiative:
            raise ValueError("Initiative not found")
        comment = InitiativeComment(initiative_id=initiative_id, user_id=user_id, body=req.body)
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def list_comments(self, org_id: UUID, initiative_id: UUID) -> list[InitiativeComment]:
        initiative = await self.get_initiative(org_id, initiative_id)
        if not initiative:
            return []
        result = await self.db.execute(
            select(InitiativeComment)
            .where(InitiativeComment.initiative_id == initiative_id)
            .order_by(InitiativeComment.created_at)
        )
        return list(result.scalars().all())

    async def get_board(self, org_id: UUID) -> InitiativeBoard:
        all_initiatives, _ = await self.list_initiatives(org_id, limit=500)
        by_status: dict[InitiativeStatus, list[InitiativeOut]] = {s: [] for s in InitiativeStatus}
        for i in all_initiatives:
            by_status[i.status].append(InitiativeOut.from_model(i))
        return InitiativeBoard(
            backlog=by_status[InitiativeStatus.BACKLOG],
            planned=by_status[InitiativeStatus.PLANNED],
            in_progress=by_status[InitiativeStatus.IN_PROGRESS],
            review=by_status[InitiativeStatus.REVIEW],
            done=by_status[InitiativeStatus.DONE],
            cancelled=by_status[InitiativeStatus.CANCELLED],
        )
