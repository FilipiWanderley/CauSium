from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from app.core.types import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PolicyBundle(Base):
    __tablename__ = "policy_bundles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0.0")
    engine: Mapped[str] = mapped_column(String(30), nullable=False, default="internal-pbac-abac")
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PolicyDecisionEvidence(Base):
    __tablename__ = "policy_decision_evidences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_bundle_id: Mapped[UUID | None] = mapped_column(ForeignKey("policy_bundles.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(120), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    session_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    policy_decision_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
