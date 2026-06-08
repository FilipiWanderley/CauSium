from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BusinessRuleType(str, enum.Enum):
    RESOURCE_GROUP = "resource_group"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    RESOURCE_NAME = "resource_name"


class CriteriaOperator(str, enum.Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class BusinessAuditAction(str, enum.Enum):
    RULE_CREATED = "RULE_CREATED"
    RULE_UPDATED = "RULE_UPDATED"
    RULE_DELETED = "RULE_DELETED"
    RULE_ACTIVATED = "RULE_ACTIVATED"
    RULE_DEACTIVATED = "RULE_DEACTIVATED"


class BusinessRule(Base):
    """Business mapping rule for cost allocation."""

    __tablename__ = "tenant_business_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_type: Mapped[BusinessRuleType] = mapped_column(
        Enum(BusinessRuleType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    criteria_field: Mapped[str] = mapped_column(String(100), nullable=False)
    criteria_operator: Mapped[CriteriaOperator] = mapped_column(
        Enum(CriteriaOperator, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    criteria_value: Mapped[str] = mapped_column(String(500), nullable=False)
    destination_team: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_cost_center: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", index=True)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class BusinessAudit(Base):
    """Audit log for business mapping changes."""

    __tablename__ = "tenant_business_audit"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action: Mapped[BusinessAuditAction] = mapped_column(
        Enum(BusinessAuditAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
