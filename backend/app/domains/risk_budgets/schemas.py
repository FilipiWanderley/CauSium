from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.risk_budgets.models import BudgetPeriod, BudgetType


class RiskBudgetCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    domain: str = Field(..., min_length=1, max_length=100)
    environment: str = Field(..., min_length=1, max_length=50)
    budget_type: BudgetType
    period: BudgetPeriod = BudgetPeriod.WEEKLY
    limit_value: float = Field(..., gt=0)


class RiskBudgetUpdate(BaseModel):
    name: Optional[str] = None
    limit_value: Optional[float] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = None
    is_active: Optional[bool] = None


class RiskBudgetOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    domain: str
    environment: str
    budget_type: BudgetType
    period: BudgetPeriod
    limit_value: float
    current_value: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
