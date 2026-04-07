from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.change_events.models import ChangeEventType


class ChangeEventCreate(BaseModel):
    event_type: ChangeEventType
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    service: Optional[str] = None
    resource_id: Optional[str] = None
    environment: str = "unknown"
    owner_team: Optional[str] = None
    region: Optional[str] = None
    account_id: Optional[UUID] = None
    external_ref: Optional[str] = None
    extra_metadata: Optional[dict] = None
    occurred_at: datetime
    cost_impact_usd: Optional[float] = None
    causal_confidence: Optional[float] = Field(None, ge=0, le=1)


class ChangeEventOut(BaseModel):
    id: UUID
    org_id: UUID
    account_id: Optional[UUID]
    event_type: ChangeEventType
    service: Optional[str]
    resource_id: Optional[str]
    environment: str
    owner_team: Optional[str]
    region: Optional[str]
    title: str
    description: Optional[str]
    cost_impact_usd: Optional[float]
    causal_confidence: Optional[float]
    external_ref: Optional[str]
    extra_metadata: Optional[dict]
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
