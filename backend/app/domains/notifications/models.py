from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
