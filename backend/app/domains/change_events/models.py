from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VC = lambda x: [e.value for e in x]  # noqa: E731


class ChangeEventType(str, enum.Enum):
    DEPLOY = "deploy"
    CONFIG_CHANGE = "config_change"
    SCALING = "scaling"
    INCIDENT = "incident"
    COST_ANOMALY = "cost_anomaly"
    POLICY_CHANGE = "policy_change"


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("cloud_accounts.id", ondelete="SET NULL"), nullable=True)

    event_type: Mapped[ChangeEventType] = mapped_column(
        Enum(ChangeEventType, values_callable=_VC), nullable=False
    )

    service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    owner_team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Causal attribution (filled later by analysis)
    cost_impact_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    causal_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1

    # External references (git sha, ticket, etc.)
    external_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
