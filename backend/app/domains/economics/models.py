from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VC = lambda x: [e.value for e in x]  # noqa: E731


class FinancialBudgetPeriod(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class ReportExportStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportExportFormat(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"


class EconomicsReportType(str, enum.Enum):
    SUMMARY = "summary"


class WorkspaceBudget(Base):
    """One configurable financial budget per workspace (org).

    Fields
    ------
    amount_usd          Total budget ceiling for the chosen period.
    period              Granularity: monthly | quarterly | annual.
    currency            ISO-4217 code displayed in the UI (default USD).
                        Cost data is always stored in USD; this is cosmetic.
    alert_thresholds    JSON-encoded list[int] of % breakpoints that trigger
                        notifications, e.g. "[50, 80, 90]".
    """

    __tablename__ = "workspace_budgets"
    __table_args__ = (UniqueConstraint("org_id", name="uq_workspace_budgets_org_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[FinancialBudgetPeriod] = mapped_column(
        Enum(FinancialBudgetPeriod, values_callable=_VC, name="financialbudgetperiod"),
        nullable=False,
        default=FinancialBudgetPeriod.MONTHLY,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # JSON-encoded list[int], e.g. "[50, 80, 90]"
    alert_thresholds: Mapped[str] = mapped_column(Text, nullable=False, default="[50, 80, 90]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReportExportJob(Base):
    __tablename__ = "report_export_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[EconomicsReportType] = mapped_column(
        Enum(EconomicsReportType, values_callable=_VC, name="economicsreporttype"),
        nullable=False,
        default=EconomicsReportType.SUMMARY,
    )
    file_format: Mapped[ReportExportFormat] = mapped_column(
        Enum(ReportExportFormat, values_callable=_VC, name="reportexportformat"),
        nullable=False,
        default=ReportExportFormat.CSV,
    )
    status: Mapped[ReportExportStatus] = mapped_column(
        Enum(ReportExportStatus, values_callable=_VC, name="reportexportstatus"),
        nullable=False,
        default=ReportExportStatus.QUEUED,
        index=True,
    )
    window_days: Mapped[int] = mapped_column(nullable=False, default=30)
    filters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
