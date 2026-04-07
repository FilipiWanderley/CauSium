from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VC = lambda x: [e.value for e in x]  # noqa: E731


class BudgetPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BudgetType(str, enum.Enum):
    BLAST_RADIUS = "blast_radius"        # % of services affected
    COST_VARIANCE = "cost_variance"      # max allowed cost change %
    ERROR_RATE = "error_rate"            # max allowed error rate
    CHANGE_FREQUENCY = "change_frequency"  # max changes per period


class RiskBudget(Base):
    __tablename__ = "risk_budgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)       # team or service name
    environment: Mapped[str] = mapped_column(String(50), nullable=False)   # production, staging, dev

    budget_type: Mapped[BudgetType] = mapped_column(
        Enum(BudgetType, values_callable=_VC), nullable=False
    )
    period: Mapped[BudgetPeriod] = mapped_column(
        Enum(BudgetPeriod, values_callable=_VC), default=BudgetPeriod.WEEKLY
    )

    limit_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # refreshed periodically
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
