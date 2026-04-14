from __future__ import annotations

from typing import Any
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.economics.models import (
    EconomicsReportType,
    FinancialBudgetPeriod,
    ReportExportFormat,
    ReportExportStatus,
)


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


class ReportExportCreate(BaseModel):
    """Payload for POST /economics/reports/export."""

    report_type: EconomicsReportType = EconomicsReportType.SUMMARY
    file_format: ReportExportFormat = ReportExportFormat.CSV
    window_days: int = Field(
        default=30,
        ge=1,
        le=366,
        description="Rolling report window in days.",
    )
    filters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional filter bag to be applied when the async export is generated.",
    )


class ReportExportJobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    requested_by_user_id: UUID
    report_type: EconomicsReportType
    file_format: ReportExportFormat
    status: ReportExportStatus
    window_days: int
    filters: Optional[dict[str, Any]]
    file_name: Optional[str]
    content_type: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    download_ready: bool = False
    created_at: datetime
    updated_at: datetime
