from __future__ import annotations
from typing import Optional, List
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import UUID as SA_UUID

from app.core.types import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProviderRecommendationStatus(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    DEFERRED = "deferred"


class ProviderRecommendation(Base):
    __tablename__ = "provider_recommendations"

    id: Mapped[UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("cloud_accounts.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    short_description: Mapped[str] = mapped_column(String(512), nullable=False)
    impact_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    annual_savings_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[ProviderRecommendationStatus] = mapped_column(
        Enum(ProviderRecommendationStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProviderRecommendationStatus.OPEN,
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncRecord(Base):
    __tablename__ = "sync_records"

    id: Mapped[UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("cloud_accounts.id"), nullable=False)
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    records_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class OpportunityCategory(str, enum.Enum):
    RIGHTSIZING = "rightsizing"
    AKS_NODEPOOL_RIGHTSIZING = "aks_nodepool_rightsizing"
    AKS_AUTOSCALER_RECOMMENDATION = "aks_autoscaler_recommendation"
    IDLE_RESOURCES = "idle_resources"
    RESERVED_INSTANCES = "reserved_instances"
    STORAGE_OPTIMIZATION = "storage_optimization"
    NETWORK_OPTIMIZATION = "network_optimization"
    LICENSE_OPTIMIZATION = "license_optimization"
    ARCHITECTURE_CHANGE = "architecture_change"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EffortLevel(str, enum.Enum):
    LOW = "low"      # < 1 day
    MEDIUM = "medium"  # 1–5 days
    HIGH = "high"    # > 5 days


class OpportunityStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    VALIDATED = "validated"


class OptimizationOpportunity(Base):
    __tablename__ = "optimization_opportunities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("cloud_accounts.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[OpportunityCategory] = mapped_column(
        Enum(OpportunityCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Scoring components (0–100)
    financial_impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    effort_score: Mapped[float] = mapped_column(Float, default=0.0)
    criticality_score: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Financial
    estimated_monthly_savings_usd: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_annual_savings_usd: Mapped[float] = mapped_column(Float, default=0.0)
    current_monthly_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Metadata
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, values_callable=lambda x: [e.value for e in x]),
        default=RiskLevel.LOW,
    )
    effort_level: Mapped[EffortLevel] = mapped_column(
        Enum(EffortLevel, values_callable=lambda x: [e.value for e in x]),
        default=EffortLevel.MEDIUM,
    )
    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus, values_callable=lambda x: [e.value for e in x]),
        default=OpportunityStatus.OPEN,
    )

    # Resource context
    resource_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resource_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sku_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    machine_family: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner_team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Explainability
    score_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    playbook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    initiatives: Mapped[list] = relationship("Initiative", back_populates="opportunity")


# Ensure SQLAlchemy resolves "Initiative" relationship in worker contexts
# where decision engine models may load before workflow models.
from app.domains.workflow import models as _workflow_models  # noqa: E402,F401


class ConfidenceCalibration(Base):
    __tablename__ = "confidence_calibrations"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "dimension_type",
            "dimension_key",
            name="uq_confidence_calibrations_org_dimension",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension_type: Mapped[str] = mapped_column(String(32), nullable=False, default="category")
    dimension_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    total_executions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cumulative_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    historical_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_adjustment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
