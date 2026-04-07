from __future__ import annotations
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.workflow.models import InitiativeStatus


class InitiativeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str | None = None
    opportunity_id: UUID | None = None
    owner_id: UUID | None = None
    sla_date: date | None = None
    external_ref: str | None = None
    external_url: str | None = None


class InitiativeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    owner_id: UUID | None = None
    sla_date: date | None = None
    external_ref: str | None = None
    external_url: str | None = None
    realized_savings_usd: float | None = None


class InitiativeStatusTransition(BaseModel):
    status: InitiativeStatus


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class CommentOut(BaseModel):
    id: UUID
    initiative_id: UUID
    user_id: UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InitiativeOut(BaseModel):
    id: UUID
    org_id: UUID
    opportunity_id: UUID | None
    owner_id: UUID | None
    title: str
    description: str | None
    status: InitiativeStatus
    sla_date: date | None
    completed_at: datetime | None
    external_ref: str | None
    external_url: str | None
    realized_savings_usd: float | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, initiative) -> "InitiativeOut":
        obj = cls.model_validate(initiative)
        if initiative.sla_date and initiative.status not in (
            InitiativeStatus.DONE, InitiativeStatus.CANCELLED
        ):
            from datetime import date
            obj.is_overdue = initiative.sla_date < date.today()
        return obj


class InitiativeBoard(BaseModel):
    backlog: list[InitiativeOut]
    planned: list[InitiativeOut]
    in_progress: list[InitiativeOut]
    review: list[InitiativeOut]
    done: list[InitiativeOut]
    cancelled: list[InitiativeOut]
