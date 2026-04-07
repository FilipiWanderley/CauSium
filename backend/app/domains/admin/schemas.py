from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domains.auth.models import UserRole, WorkspaceLifecycleState


class AdminOrgListItem(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    lifecycle_state: WorkspaceLifecycleState
    member_quota: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserItem(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class AdminForceLifecycle(BaseModel):
    reason: str
