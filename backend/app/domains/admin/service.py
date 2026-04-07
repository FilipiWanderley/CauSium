from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_pool
from app.core.schemas import PageParams
from app.domains.admin.models import DlqMessage, DlqStatus
from app.domains.audit_chain.service import AuditChainService
from app.domains.auth.models import Organization, User, WorkspaceLifecycleState


class PlatformAdminService:
    def __init__(self, db: AsyncSession, actor_user_id: UUID) -> None:
        self.db = db
        self.actor_user_id = actor_user_id
        self.audit_chain = AuditChainService(db)

    async def list_orgs(self, params: PageParams) -> tuple[list[Organization], int]:
        count_result = await self.db.execute(select(func.count(Organization.id)))
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(Organization)
            .order_by(Organization.created_at.desc())
            .limit(params.limit)
            .offset(params.offset)
        )
        return list(items_result.scalars().all()), total

    async def get_org(self, org_id: UUID) -> Organization:
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
        return org

    async def list_org_users(self, org_id: UUID, params: PageParams) -> tuple[list[User], int]:
        await self.get_org(org_id)  # ensure exists

        count_result = await self.db.execute(
            select(func.count(User.id)).where(User.org_id == org_id)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(User)
            .where(User.org_id == org_id)
            .order_by(User.created_at.desc())
            .limit(params.limit)
            .offset(params.offset)
        )
        return list(items_result.scalars().all()), total

    async def force_suspend(self, org_id: UUID, reason: str) -> Organization:
        org = await self.get_org(org_id)
        if org.lifecycle_state == WorkspaceLifecycleState.ARCHIVED:
            raise HTTPException(status.HTTP_409_CONFLICT, "Archived workspaces cannot be suspended.")
        if org.lifecycle_state == WorkspaceLifecycleState.SUSPENDED:
            raise HTTPException(status.HTTP_409_CONFLICT, "Workspace is already suspended.")

        previous_state = org.lifecycle_state
        org.lifecycle_state = WorkspaceLifecycleState.SUSPENDED
        org.suspended_at = datetime.now(timezone.utc)
        org.suspended_reason = reason
        await self.db.flush()

        await self._audit(
            org_id=org_id,
            event_type="platform_admin.workspace.force_suspended",
            payload={"from": previous_state.value, "to": "suspended", "reason": reason},
        )
        await self.db.refresh(org)
        return org

    async def force_restore(self, org_id: UUID, reason: str) -> Organization:
        org = await self.get_org(org_id)
        if org.lifecycle_state == WorkspaceLifecycleState.ARCHIVED:
            raise HTTPException(status.HTTP_409_CONFLICT, "Archived workspaces cannot be restored.")
        if org.lifecycle_state == WorkspaceLifecycleState.ACTIVE:
            raise HTTPException(status.HTTP_409_CONFLICT, "Workspace is already active.")

        org.lifecycle_state = WorkspaceLifecycleState.ACTIVE
        org.suspended_at = None
        org.suspended_reason = None
        await self.db.flush()

        await self._audit(
            org_id=org_id,
            event_type="platform_admin.workspace.force_restored",
            payload={"to": "active", "reason": reason},
        )
        await self.db.refresh(org)
        return org

    async def force_archive(self, org_id: UUID, reason: str) -> Organization:
        org = await self.get_org(org_id)
        if org.lifecycle_state == WorkspaceLifecycleState.ARCHIVED:
            raise HTTPException(status.HTTP_409_CONFLICT, "Workspace is already archived.")

        previous_state = org.lifecycle_state
        org.lifecycle_state = WorkspaceLifecycleState.ARCHIVED
        await self.db.flush()

        await self._audit(
            org_id=org_id,
            event_type="platform_admin.workspace.force_archived",
            payload={"from": previous_state.value, "to": "archived", "reason": reason},
        )
        await self.db.refresh(org)
        return org

    async def _audit(self, *, org_id: UUID, event_type: str, payload: dict) -> None:
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=self.actor_user_id,
            event_type=event_type,
            entity_type="organization",
            entity_id=str(org_id),
            payload=payload,
        )

    async def list_dlq(self, params: PageParams) -> tuple[list[DlqMessage], int]:
        count_result = await self.db.execute(select(func.count(DlqMessage.id)))
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(DlqMessage)
            .order_by(DlqMessage.created_at.desc())
            .limit(params.limit)
            .offset(params.offset)
        )
        return list(result.scalars().all()), total

    async def requeue_dlq(self, dlq_id: UUID) -> DlqMessage:
        result = await self.db.execute(select(DlqMessage).where(DlqMessage.id == dlq_id))
        msg = result.scalar_one_or_none()
        if not msg:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "DLQ message not found")

        redis = get_redis_pool()
        await redis.lpush(msg.queue_name, msg.original_payload)
        msg.status = DlqStatus.REQUEUED
        await self.db.flush()
        await self.db.refresh(msg)
        return msg
