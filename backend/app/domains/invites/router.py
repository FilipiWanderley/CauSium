from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.schemas import Page, PageParams
from app.domains.auth.models import User, UserRole
from app.domains.auth.schemas import UserOut
from app.domains.invites.schemas import InviteAccept, InviteCreate, InviteOut, InvitePreview
from app.domains.invites.service import InviteService

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(
    req: InviteCreate,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InviteOut:
    service = InviteService(db)
    invite = await service.create_invite(current_user.org_id, current_user.id, req)
    await db.commit()
    return invite


@router.get("/{token}/preview", response_model=InvitePreview)
async def preview_invite(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvitePreview:
    from app.domains.auth.service import AuthService

    service = InviteService(db)
    invite = await service.get_by_token(token)
    await db.commit()  # persist any auto-expiry flush

    auth_service = AuthService(db)
    org = await auth_service.get_org(invite.org_id)
    return InvitePreview(
        org_name=org.name if org else "",
        invited_email=invite.invited_email,
        role=invite.role,
        expires_at=invite.expires_at,
        status=invite.status,
    )


@router.post("/{token}/accept", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def accept_invite(
    token: str,
    req: InviteAccept,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    from app.domains.auth.service import AuthService

    service = InviteService(db)
    user = await service.accept_invite(token, req)
    await db.commit()

    auth_service = AuthService(db)
    org_name = await auth_service.get_org_name(user.org_id)
    out = UserOut.model_validate(user)
    out.org_name = org_name
    return out


@router.get("", response_model=Page[InviteOut])
async def list_invites(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    params: Annotated[PageParams, Depends(PageParams)],
) -> Page[InviteOut]:
    service = InviteService(db)
    items, total = await service.list_invites(current_user.org_id, params)
    return Page.of(items, total, params)


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InviteService(db)
    await service.revoke_invite(current_user.org_id, invite_id, current_user.id)
    await db.commit()
