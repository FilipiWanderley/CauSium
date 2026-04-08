from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.email import EmailService
from app.core.schemas import PageParams
from app.core.security import hash_password
from app.domains.audit_chain.service import AuditChainService
from app.domains.auth.models import Organization, User
from app.domains.invites.models import InviteStatus, WorkspaceInvite
from app.domains.invites.schemas import InviteAccept, InviteCreate


class InviteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit_chain = AuditChainService(db)
        self.email = EmailService()

    async def create_invite(
        self,
        org_id: UUID,
        actor_user_id: UUID,
        req: InviteCreate,
    ) -> WorkspaceInvite:
        org = await self._get_org(org_id)
        if not org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

        active_count = await self._count_active_members(org_id)
        if active_count >= org.member_quota:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Member quota reached ({org.member_quota} active users). "
                "Upgrade your workspace plan to invite more members.",
            )

        existing = await self._get_pending_by_email(org_id, req.email)
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"A pending invite for {req.email} already exists.",
            )

        invite = WorkspaceInvite(
            org_id=org_id,
            invited_email=req.email,
            invited_by_user_id=actor_user_id,
            role=req.role,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(days=req.expires_in_days),
            status=InviteStatus.PENDING,
        )
        self.db.add(invite)
        await self.db.flush()

        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="invite.created",
            entity_type="workspace_invite",
            entity_id=str(invite.id),
            payload={
                "invited_email": req.email,
                "role": req.role.value,
                "expires_in_days": req.expires_in_days,
            },
        )

        # SP-AP03: send workspace invite email when SMTP is enabled.
        accept_url = f"{get_settings().frontend_url}/activate?token={invite.token}"
        await self.email.send_email(
            to_email=req.email,
            subject="[StratoPulse] Voce foi convidado para um workspace",
            text_body=(
                "Voce recebeu um convite para entrar em um workspace no StratoPulse.\n\n"
                f"Funcao: {req.role.value}\n"
                f"Aceitar convite: {accept_url}\n"
                f"Expira em: {invite.expires_at.isoformat()}\n"
            ),
        )

        await self.db.refresh(invite)
        return invite

    async def get_by_token(self, token: str) -> WorkspaceInvite:
        result = await self.db.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.token == token)
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")

        if invite.status == InviteStatus.PENDING and datetime.now(timezone.utc) > invite.expires_at:
            invite.status = InviteStatus.EXPIRED
            await self.db.flush()

        return invite

    async def accept_invite(self, token: str, req: InviteAccept) -> User:
        invite = await self.get_by_token(token)
        if invite.status != InviteStatus.PENDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Invite is {invite.status.value} and cannot be accepted.",
            )

        org = await self._get_org(invite.org_id)
        if not org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

        active_count = await self._count_active_members(invite.org_id)
        if active_count >= org.member_quota:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Member quota reached. Contact your workspace admin.",
            )

        existing_user = await self.db.execute(
            select(User).where(User.email == invite.invited_email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An account with this email already exists.",
            )

        user = User(
            org_id=invite.org_id,
            email=invite.invited_email,
            full_name=req.full_name,
            hashed_password=hash_password(req.password),
            role=invite.role,
        )
        self.db.add(user)

        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self.audit_chain.append_event(
            org_id=invite.org_id,
            actor_user_id=user.id,
            event_type="invite.accepted",
            entity_type="workspace_invite",
            entity_id=str(invite.id),
            payload={"invited_email": invite.invited_email, "role": invite.role.value},
        )
        await self.db.refresh(user)
        return user

    async def list_invites(
        self,
        org_id: UUID,
        params: PageParams,
    ) -> tuple[list[WorkspaceInvite], int]:
        now = datetime.now(timezone.utc)
        stale_result = await self.db.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.org_id == org_id,
                WorkspaceInvite.status == InviteStatus.PENDING,
                WorkspaceInvite.expires_at < now,
            )
        )
        for stale in stale_result.scalars().all():
            stale.status = InviteStatus.EXPIRED

        count_result = await self.db.execute(
            select(func.count(WorkspaceInvite.id)).where(WorkspaceInvite.org_id == org_id)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(WorkspaceInvite)
            .where(WorkspaceInvite.org_id == org_id)
            .order_by(WorkspaceInvite.created_at.desc())
            .limit(params.limit)
            .offset(params.offset)
        )
        return list(items_result.scalars().all()), total

    async def revoke_invite(
        self,
        org_id: UUID,
        invite_id: UUID,
        actor_user_id: UUID,
    ) -> WorkspaceInvite:
        result = await self.db.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.org_id == org_id,
            )
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")

        if invite.status != InviteStatus.PENDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Only pending invites can be revoked; current status is {invite.status.value}.",
            )

        invite.status = InviteStatus.REVOKED
        await self.db.flush()

        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="invite.revoked",
            entity_type="workspace_invite",
            entity_id=str(invite.id),
            payload={"invited_email": invite.invited_email},
        )
        await self.db.refresh(invite)
        return invite

    # --- private helpers ---

    async def _get_org(self, org_id: UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def _count_active_members(self, org_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(User.id)).where(User.org_id == org_id, User.is_active == True)  # noqa: E712
        )
        return result.scalar_one()

    async def _get_pending_by_email(self, org_id: UUID, email: str) -> WorkspaceInvite | None:
        result = await self.db.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.org_id == org_id,
                WorkspaceInvite.invited_email == email,
                WorkspaceInvite.status == InviteStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()
