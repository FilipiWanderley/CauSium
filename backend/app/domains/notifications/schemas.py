from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.notifications.models import (
    AlertCategory,
    ActivityEventSeverity,
    AlertSeverity,
    AlertStatus,
    NotificationFrequency,
)


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


class NotificationPreferenceOut(BaseModel):
    in_app_enabled: bool
    email_enabled: bool
    slack_enabled: bool
    frequency: NotificationFrequency
    categories: Optional[dict]

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    slack_enabled: Optional[bool] = None
    frequency: Optional[NotificationFrequency] = None
    categories: Optional[dict] = None


class NotificationSlackConfigOut(BaseModel):
    enabled: bool
    webhook_configured: bool


class NotificationSlackConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    webhook_url: Optional[str] = None


class ActivityEventCreate(BaseModel):
    provider: str = Field(default="unknown", min_length=2, max_length=50)
    event_type: str = Field(..., min_length=2, max_length=120)
    severity: ActivityEventSeverity = ActivityEventSeverity.INFO
    title: str = Field(..., min_length=3, max_length=500)
    body: Optional[str] = None
    service: Optional[str] = Field(default=None, max_length=100)
    resource_id: Optional[str] = Field(default=None, max_length=255)
    account_id: Optional[UUID] = None
    extra_metadata: Optional[dict] = None
    occurred_at: datetime


class ActivityEventOut(BaseModel):
    id: UUID
    org_id: UUID
    account_id: Optional[UUID]
    provider: str
    event_type: str
    severity: ActivityEventSeverity
    service: Optional[str]
    resource_id: Optional[str]
    title: str
    body: Optional[str]
    extra_metadata: Optional[dict]
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationAlertRuleOut(BaseModel):
    category: AlertCategory
    enabled: bool
    min_severity: AlertSeverity
    event_type_prefix: Optional[str]

    model_config = {"from_attributes": True}


class NotificationAlertRuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    min_severity: Optional[AlertSeverity] = None
    event_type_prefix: Optional[str] = Field(default=None, max_length=120)
