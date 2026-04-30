from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_pool
from app.core.schemas import PageParams
from app.domains.admin.models import DlqMessage, DlqStatus, SupportAccessSession, SupportAccessStatus
from app.domains.audit_chain.service import AuditChainService
from app.domains.auth.models import Organization, User, UserRole, WorkspaceLifecycleState


class PlatformAdminService:
    MAX_SUPPORT_ACCESS_MINUTES = 60

    def __init__(self, db: AsyncSession, actor_user_id: UUID) -> None:
        self.db = db
        self.actor_user_id = actor_user_id
        self.audit_chain = AuditChainService(db)

    async def list_orgs(
        self,
        params: PageParams,
        *,
        q: str | None = None,
        lifecycle_state: WorkspaceLifecycleState | None = None,
    ) -> tuple[list[Organization], int]:
        filters = []
        if q:
            needle = f"%{q.strip()}%"
            filters.append((Organization.name.ilike(needle)) | (Organization.slug.ilike(needle)))
        if lifecycle_state:
            filters.append(Organization.lifecycle_state == lifecycle_state)

        count_result = await self.db.execute(select(func.count(Organization.id)).where(*filters))
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(Organization)
            .where(*filters)
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

    async def create_support_access_session(
        self,
        *,
        target_org_id: UUID,
        reason: str,
        duration_minutes: int,
    ) -> SupportAccessSession:
        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Reason is required.")
        if duration_minutes < 1 or duration_minutes > self.MAX_SUPPORT_ACCESS_MINUTES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"duration_minutes must be between 1 and {self.MAX_SUPPORT_ACCESS_MINUTES}.",
            )

        await self.get_org(target_org_id)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=duration_minutes)
        session = SupportAccessSession(
            actor_user_id=self.actor_user_id,
            target_org_id=target_org_id,
            reason=cleaned_reason,
            status=SupportAccessStatus.ACTIVE,
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        await self._audit(
            org_id=target_org_id,
            event_type="support_access.started",
            payload={
                "support_access_session_id": str(session.id),
                "actor_user_id": str(self.actor_user_id),
                "target_org_id": str(target_org_id),
                "reason": cleaned_reason,
                "duration_minutes": duration_minutes,
                "expires_at": session.expires_at.isoformat(),
            },
        )
        return session

    async def list_active_support_access_sessions(self) -> list[SupportAccessSession]:
        await self._expire_stale_support_sessions()
        result = await self.db.execute(
            select(SupportAccessSession)
            .where(SupportAccessSession.status == SupportAccessStatus.ACTIVE)
            .order_by(SupportAccessSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def end_support_access_session(self, session_id: UUID, *, reason: str) -> SupportAccessSession:
        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Reason is required.")

        session = await self._get_support_session(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Support access session not found.")

        if session.status == SupportAccessStatus.ENDED:
            raise HTTPException(status.HTTP_409_CONFLICT, "Support access session already ended.")

        now = datetime.now(timezone.utc)
        if session.status == SupportAccessStatus.EXPIRED or session.expires_at <= now:
            session.status = SupportAccessStatus.EXPIRED
            session.ended_at = session.ended_at or now
            await self.db.flush()
            raise HTTPException(status.HTTP_409_CONFLICT, "Support access session already expired.")

        session.status = SupportAccessStatus.ENDED
        session.ended_at = now
        await self.db.flush()
        await self.db.refresh(session)

        await self._audit(
            org_id=session.target_org_id,
            event_type="support_access.ended",
            payload={
                "support_access_session_id": str(session.id),
                "actor_user_id": str(self.actor_user_id),
                "target_org_id": str(session.target_org_id),
                "reason": cleaned_reason,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            },
        )
        return session

    async def resolve_active_support_access_session(
        self,
        session_id: UUID,
    ) -> SupportAccessSession:
        session = await self._get_support_session(session_id)
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Support access session not found.")
        if session.actor_user_id != self.actor_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Support access session belongs to another actor.")

        now = datetime.now(timezone.utc)
        if session.status != SupportAccessStatus.ACTIVE or session.expires_at <= now:
            if session.status == SupportAccessStatus.ACTIVE and session.expires_at <= now:
                session.status = SupportAccessStatus.EXPIRED
                session.ended_at = session.ended_at or now
                await self.db.flush()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Support access session is not active.")
        return session

    async def _get_support_session(self, session_id: UUID) -> SupportAccessSession | None:
        result = await self.db.execute(
            select(SupportAccessSession).where(SupportAccessSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _expire_stale_support_sessions(self) -> None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(SupportAccessSession).where(
                and_(
                    SupportAccessSession.status == SupportAccessStatus.ACTIVE,
                    SupportAccessSession.expires_at <= now,
                )
            )
        )
        stale_sessions = list(result.scalars().all())
        for session in stale_sessions:
            session.status = SupportAccessStatus.EXPIRED
            session.ended_at = session.ended_at or now
        if stale_sessions:
            await self.db.flush()

    async def seed_platform_admin(self, email: str, full_name: str) -> tuple[bool, bool]:
        """Promote email to PLATFORM_ADMIN, creating the user if needed.

        Returns (created, promoted) — both False if user already had the role.
        """
        import uuid
        from app.core.security import hash_password

        result = await self.db.execute(select(User).where(User.email == email.lower().strip()))
        user = result.scalar_one_or_none()

        created = False
        promoted = False

        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=email.lower().strip(),
                full_name=full_name,
                hashed_password=hash_password(uuid.uuid4().hex),
                role=UserRole.PLATFORM_ADMIN,
                is_active=True,
            )
            self.db.add(user)
            created = True
            promoted = True
        elif user.role != UserRole.PLATFORM_ADMIN:
            user.role = UserRole.PLATFORM_ADMIN
            promoted = True

        await self.db.flush()
        return created, promoted
