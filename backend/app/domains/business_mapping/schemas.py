from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.business_mapping.models import BusinessAuditAction, BusinessRuleType, CriteriaOperator


class BusinessRuleBase(BaseModel):
    """Base schema for business rules."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    rule_type: BusinessRuleType
    criteria_field: str = Field(..., min_length=1, max_length=100)
    criteria_operator: CriteriaOperator
    criteria_value: str = Field(..., min_length=1, max_length=500)
    destination_team: str = Field(..., min_length=1, max_length=255)
    destination_cost_center: str | None = Field(None, max_length=255)
    priority: int = Field(default=100, ge=1, le=1000)


class BusinessRuleCreate(BusinessRuleBase):
    """Schema for creating a business rule."""

    pass


class BusinessRuleUpdate(BaseModel):
    """Schema for updating a business rule."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    criteria_field: str | None = Field(None, min_length=1, max_length=100)
    criteria_operator: CriteriaOperator | None = None
    criteria_value: str | None = Field(None, min_length=1, max_length=500)
    destination_team: str | None = Field(None, min_length=1, max_length=255)
    destination_cost_center: str | None = Field(None, max_length=255)
    priority: int | None = Field(None, ge=1, le=1000)


class BusinessRuleOut(BusinessRuleBase):
    """Schema for business rule response."""

    id: UUID
    org_id: UUID
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime | None
    updated_by: UUID | None

    model_config = ConfigDict(from_attributes=True)


class BusinessRuleListOut(BaseModel):
    """Schema for paginated business rule list."""

    id: UUID
    name: str
    rule_type: BusinessRuleType
    destination_team: str
    priority: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessAuditOut(BaseModel):
    """Schema for audit log entry."""

    id: UUID
    org_id: UUID
    entity_type: str
    entity_id: UUID
    action: BusinessAuditAction
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
