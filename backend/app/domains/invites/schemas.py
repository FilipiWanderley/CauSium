from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.domains.auth.models import UserRole
from app.domains.invites.models import InviteStatus


class InviteCreate(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.VIEWER
    expires_in_days: int = Field(7, ge=1, le=30)


class InvitePreview(BaseModel):
    org_name: str
    invited_email: str
    role: UserRole
    expires_at: datetime
    status: InviteStatus


class InviteAccept(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)


class InviteOut(BaseModel):
    id: UUID
    org_id: UUID
    invited_email: str
    invited_by_user_id: UUID
    role: UserRole
    token: str
    expires_at: datetime
    accepted_at: datetime | None
    status: InviteStatus
    created_at: datetime

    model_config = {"from_attributes": True}
