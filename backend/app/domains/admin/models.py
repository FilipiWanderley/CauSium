from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DlqStatus(str, enum.Enum):
    OPEN = "open"
    REQUEUED = "requeued"
    RESOLVED = "resolved"


class SupportAccessStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"


class DlqMessage(Base):
    __tablename__ = "dlq_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    queue_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    account_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    original_payload: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[DlqStatus] = mapped_column(
        Enum(DlqStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DlqStatus.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SupportAccessSession(Base):
    __tablename__ = "support_access_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SupportAccessStatus] = mapped_column(
        Enum(SupportAccessStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SupportAccessStatus.ACTIVE,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
