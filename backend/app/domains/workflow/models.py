from __future__ import annotations
from typing import Optional, List
import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InitiativeStatus(str, enum.Enum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[InitiativeStatus, list[InitiativeStatus]] = {
    InitiativeStatus.BACKLOG: [InitiativeStatus.PLANNED, InitiativeStatus.CANCELLED],
    InitiativeStatus.PLANNED: [InitiativeStatus.IN_PROGRESS, InitiativeStatus.BACKLOG, InitiativeStatus.CANCELLED],
    InitiativeStatus.IN_PROGRESS: [InitiativeStatus.REVIEW, InitiativeStatus.PLANNED, InitiativeStatus.CANCELLED],
    InitiativeStatus.REVIEW: [InitiativeStatus.DONE, InitiativeStatus.IN_PROGRESS],
    InitiativeStatus.DONE: [],
    InitiativeStatus.CANCELLED: [InitiativeStatus.BACKLOG],
}


class Initiative(Base):
    __tablename__ = "initiatives"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    opportunity_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("optimization_opportunities.id"), nullable=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[InitiativeStatus] = mapped_column(Enum(InitiativeStatus, values_callable=lambda x: [e.value for e in x]), default=InitiativeStatus.BACKLOG)

    sla_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # External integration (Jira/Linear/GitHub)
    external_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Realized savings (filled when done/validated)
    realized_savings_usd: Mapped[Optional[float]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    opportunity: Mapped = relationship("OptimizationOpportunity", back_populates="initiatives")
    owner: Mapped = relationship("User", foreign_keys=[owner_id])
    comments: Mapped[list["InitiativeComment"]] = relationship(
        "InitiativeComment", back_populates="initiative", cascade="all, delete-orphan"
    )


class InitiativeComment(Base):
    __tablename__ = "initiative_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    initiative_id: Mapped[UUID] = mapped_column(
        ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    initiative: Mapped[Initiative] = relationship("Initiative", back_populates="comments")
    user: Mapped = relationship("User", foreign_keys=[user_id])
