from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from app.core.types import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditChainEvent(Base):
    __tablename__ = "audit_chain_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prev_hash: Mapped[str] = mapped_column(Text, nullable=False)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class AuditChainCheckpoint(Base):
    __tablename__ = "audit_chain_checkpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    latest_event_hash: Mapped[str] = mapped_column(Text, nullable=False)
    checked_events: Mapped[int] = mapped_column(nullable=False)
    snapshot_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    snapshot_signature: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
