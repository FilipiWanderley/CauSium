from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.domains.notifications.models import AlertCategory, AlertSeverity, AlertStatus


class AlertRecordOut(BaseModel):
    id: UUID
    org_id: UUID
    user_id: Optional[UUID]
    category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus
    title: str
    body: Optional[str]
    action_url: Optional[str]
    source_type: Optional[str]
    source_id: Optional[str]
    read_at: Optional[datetime]
    archived_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertStatusPatch(BaseModel):
    status: AlertStatus


class UnreadCountOut(BaseModel):
    unread: int
    critical: int


class NotificationsNewOut(BaseModel):
    unread: int
    critical: int
    total: int
    items: list[AlertRecordOut]
