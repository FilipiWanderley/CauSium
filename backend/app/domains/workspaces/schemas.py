from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.auth.models import WorkspaceLifecycleState


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    lifecycle_state: WorkspaceLifecycleState
    member_quota: int
    suspended_at: datetime | None
    suspended_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceLifecycleUpdate(BaseModel):
    lifecycle_state: WorkspaceLifecycleState
    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Required when suspending; optional for other transitions.",
    )
