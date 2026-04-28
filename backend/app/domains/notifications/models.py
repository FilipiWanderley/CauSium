from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from app.core.types import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VC = lambda x: [e.value for e in x]  # noqa: E731


class AlertCategory(str, enum.Enum):
    FINANCIAL = "financial"
    OPTIMIZATION = "optimization"
    GOVERNANCE = "governance"
    ACTIVITY = "activity"
    SECURITY = "security"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class NotificationFrequency(str, enum.Enum):
    INSTANT = "instant"
    DAILY = "daily"
    WEEKLY = "weekly"


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # If scoped to a specific user; NULL = workspace-wide
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    category: Mapped[AlertCategory] = mapped_column(
        Enum(AlertCategory, values_callable=_VC), nullable=False, index=True
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, values_callable=_VC),
        nullable=False,
        default=AlertSeverity.INFO,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, values_callable=_VC),
        nullable=False,
        default=AlertStatus.UNREAD,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional deep-link inside the app
    action_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Source reference (e.g. risk_budget_id, opportunity_id)
    source_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Delivery tracking — set once sent, prevents duplicate dispatches
    email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    slack_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_notification_preferences_org_user"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    in_app_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frequency: Mapped[NotificationFrequency] = mapped_column(
        Enum(NotificationFrequency, values_callable=_VC),
        nullable=False,
        default=NotificationFrequency.INSTANT,
    )
    categories: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class NotificationSlackConfig(Base):
    __tablename__ = "notification_slack_configs"
    __table_args__ = (
        UniqueConstraint("org_id", name="uq_notification_slack_configs_org"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    webhook_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ActivityEventSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("cloud_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    severity: Mapped[ActivityEventSeverity] = mapped_column(
        Enum(ActivityEventSeverity, values_callable=_VC),
        nullable=False,
        default=ActivityEventSeverity.INFO,
        index=True,
    )

    service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class NotificationAlertRule(Base):
    __tablename__ = "notification_alert_rules"
    __table_args__ = (
        UniqueConstraint("org_id", "category", name="uq_notification_alert_rules_org_category"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[AlertCategory] = mapped_column(
        Enum(AlertCategory, values_callable=_VC), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, values_callable=_VC),
        nullable=False,
        default=AlertSeverity.CRITICAL,
    )
    event_type_prefix: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
