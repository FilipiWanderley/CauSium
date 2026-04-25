from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.decision_engine.models import ConfidenceCalibration, OpportunityCategory


@dataclass(frozen=True)
class CalibrationSnapshot:
    historical_accuracy: float
    confidence_adjustment: float
    total_executions: int


class ConfidenceCalibrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_category_result(
        self,
        *,
        org_id: UUID,
        category: OpportunityCategory,
        expected_savings: float,
        actual_savings: float,
    ) -> CalibrationSnapshot:
        dimension_type = "category"
        dimension_key = category.value
        accuracy = _compute_accuracy(expected_savings=expected_savings, actual_savings=actual_savings)

        result = await self.db.execute(
            select(ConfidenceCalibration).where(
                ConfidenceCalibration.org_id == org_id,
                ConfidenceCalibration.dimension_type == dimension_type,
                ConfidenceCalibration.dimension_key == dimension_key,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ConfidenceCalibration(
                org_id=org_id,
                dimension_type=dimension_type,
                dimension_key=dimension_key,
                total_executions=0,
                cumulative_accuracy=0.0,
                historical_accuracy=0.0,
                confidence_adjustment=0.0,
            )
            self.db.add(row)
            await self.db.flush()

        row.total_executions = int(row.total_executions or 0) + 1
        row.cumulative_accuracy = float(row.cumulative_accuracy or 0.0) + accuracy
        row.historical_accuracy = round(row.cumulative_accuracy / max(row.total_executions, 1), 4)
        row.confidence_adjustment = _compute_adjustment(row.historical_accuracy)
        await self.db.flush()
        return CalibrationSnapshot(
            historical_accuracy=row.historical_accuracy,
            confidence_adjustment=row.confidence_adjustment,
            total_executions=row.total_executions,
        )

    async def get_category_snapshots(
        self, *, org_id: UUID, categories: set[OpportunityCategory]
    ) -> dict[OpportunityCategory, CalibrationSnapshot]:
        if not categories:
            return {}
        result = await self.db.execute(
            select(ConfidenceCalibration).where(
                ConfidenceCalibration.org_id == org_id,
                ConfidenceCalibration.dimension_type == "category",
                ConfidenceCalibration.dimension_key.in_([category.value for category in categories]),
            )
        )
        rows = list(result.scalars().all())
        out: dict[OpportunityCategory, CalibrationSnapshot] = {}
        for row in rows:
            try:
                category = OpportunityCategory(row.dimension_key)
            except ValueError:
                continue
            out[category] = CalibrationSnapshot(
                historical_accuracy=float(row.historical_accuracy or 0.0),
                confidence_adjustment=float(row.confidence_adjustment or 0.0),
                total_executions=int(row.total_executions or 0),
            )
        return out


def _compute_accuracy(*, expected_savings: float, actual_savings: float) -> float:
    if expected_savings <= 0:
        return 0.0
    ratio = actual_savings / expected_savings
    return round(max(0.0, min(1.2, ratio)), 4)


def _compute_adjustment(historical_accuracy: float) -> float:
    if historical_accuracy > 0.8:
        return 0.06
    if historical_accuracy < 0.5:
        return -0.08
    return 0.0
