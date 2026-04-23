from __future__ import annotations

import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VC = lambda x: [e.value for e in x]  # noqa: E731


class CostAnomalySeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CostAnomaly(Base):
    __tablename__ = "cost_anomalies"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "provider",
            "service",
            "observed_date",
            name="uq_cost_anomalies_org_provider_service_date",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="unknown")
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True, default="unknown")
    observed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    current_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    historical_mean_usd: Mapped[float] = mapped_column(Float, nullable=False)
    historical_stddev_usd: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[CostAnomalySeverity] = mapped_column(
        Enum(CostAnomalySeverity, values_callable=_VC), nullable=False, index=True
    )

    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    z_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
