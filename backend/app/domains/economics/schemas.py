from __future__ import annotations

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.economics.models import FinancialBudgetPeriod


class WorkspaceBudgetUpsert(BaseModel):
    """Payload for PUT /economics/budget."""

    amount_usd: float = Field(..., gt=0, description="Total budget ceiling in USD")
    period: FinancialBudgetPeriod = FinancialBudgetPeriod.MONTHLY
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="ISO-4217 currency code (display only; data always stored in USD)",
    )
    alert_thresholds: list[int] = Field(
        default=[50, 80, 90],
        description="Percent breakpoints that trigger budget alerts, e.g. [50, 80, 90]",
    )

    @field_validator("alert_thresholds")
    @classmethod
    def validate_thresholds(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("alert_thresholds must contain at least one value")
        for t in v:
            if not (1 <= t <= 100):
                raise ValueError("Each threshold must be between 1 and 100")
        return sorted(set(v))


class WorkspaceBudgetOut(BaseModel):
    """Serialised budget enriched with live consumption metrics."""

    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    amount_usd: float
    period: FinancialBudgetPeriod
    currency: str
    alert_thresholds: list[int]
    created_at: datetime
    updated_at: datetime

    # Live consumption — computed by EconomicsService, not persisted
    consumed_usd: float = 0.0
    consumed_pct: float = 0.0
    projected_eom_usd: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def decode_thresholds(cls, data: object) -> object:
        """Decode alert_thresholds from JSON string when building from ORM."""
        if hasattr(data, "__dict__"):
            raw = getattr(data, "alert_thresholds", None)
            if isinstance(raw, str):
                data = {
                    **{
                        k: getattr(data, k)
                        for k in [
                            "id",
                            "org_id",
                            "amount_usd",
                            "period",
                            "currency",
                            "created_at",
                            "updated_at",
                        ]
                    },
                    "alert_thresholds": json.loads(raw),
                }
        elif isinstance(data, dict) and isinstance(data.get("alert_thresholds"), str):
            data = {**data, "alert_thresholds": json.loads(data["alert_thresholds"])}
        return data
