from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import sqrt
from typing import Iterable
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.intel.models import CostAnomaly, CostAnomalySeverity
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService

log = get_logger(__name__)


@dataclass(frozen=True)
class CostAnomalySignal:
    provider: str
    service: str
    observed_date: date
    current_cost_usd: float
    historical_mean_usd: float
    historical_stddev_usd: float
    z_score: float
    deviation_pct: float | None
    severity: CostAnomalySeverity
    window_days: int
    z_threshold: float


@dataclass(frozen=True)
class CostAnomalyRunResult:
    observed_date: date | None
    scanned_services: int
    detected: int
    created: int
    anomalies: list[CostAnomaly]


def detect_cost_anomaly_signal(
    *,
    provider: str,
    service: str,
    observed_date: date,
    current_cost_usd: float,
    history_costs_usd: Iterable[float],
    z_threshold: float,
    min_delta_usd: float,
    window_days: int,
) -> CostAnomalySignal | None:
    history_values = [max(float(v), 0.0) for v in history_costs_usd]
    if not history_values:
        return None

    history_count = len(history_values)
    mean = sum(history_values) / history_count
    variance = sum((v - mean) ** 2 for v in history_values) / history_count
    stddev = sqrt(max(variance, 0.0))

    current = max(float(current_cost_usd), 0.0)
    delta = current - mean
    if current <= 0.0 or delta < min_delta_usd:
        return None

    if stddev <= 1e-9:
        if mean <= 0.0:
            z_score = 10.0
        else:
            z_score = 10.0 if (current / mean) >= 2.0 else 0.0
    else:
        z_score = delta / stddev

    if z_score < z_threshold:
        return None

    deviation_pct = ((delta / mean) * 100.0) if mean > 0 else None
    severity = _severity_from_z(z_score)

    return CostAnomalySignal(
        provider=(provider or "unknown").lower(),
        service=service or "unknown",
        observed_date=observed_date,
        current_cost_usd=round(current, 4),
        historical_mean_usd=round(mean, 4),
        historical_stddev_usd=round(stddev, 4),
        z_score=round(z_score, 4),
        deviation_pct=round(deviation_pct, 2) if deviation_pct is not None else None,
        severity=severity,
        window_days=window_days,
        z_threshold=z_threshold,
    )


def _severity_from_z(z_score: float) -> CostAnomalySeverity:
    if z_score >= 6.0:
        return CostAnomalySeverity.HIGH
    if z_score >= 4.0:
        return CostAnomalySeverity.MEDIUM
    return CostAnomalySeverity.LOW


def _to_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class CostAnomalyDetectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        settings = get_settings()
        self.default_lookback_days = settings.anomaly_detection_lookback_days
        self.default_z_threshold = settings.anomaly_detection_zscore_threshold
        self.default_min_history_days = settings.anomaly_detection_min_history_days
        self.default_min_delta_usd = settings.anomaly_detection_min_delta_usd

    async def detect_for_org(
        self,
        *,
        org_id: UUID,
        lookback_days: int | None = None,
        z_threshold: float | None = None,
        min_history_days: int | None = None,
        min_delta_usd: float | None = None,
    ) -> CostAnomalyRunResult:
        lookback = max(7, int(lookback_days if lookback_days is not None else self.default_lookback_days))
        threshold = float(z_threshold if z_threshold is not None else self.default_z_threshold)
        history_min = max(3, int(min_history_days if min_history_days is not None else self.default_min_history_days))
        delta_floor = max(0.0, float(min_delta_usd if min_delta_usd is not None else self.default_min_delta_usd))

        observed_date = self._fetch_latest_cost_date(org_id)
        if observed_date is None:
            return CostAnomalyRunResult(
                observed_date=None, scanned_services=0, detected=0, created=0, anomalies=[]
            )

        window_start = observed_date - timedelta(days=lookback)
        series_by_service = self._fetch_daily_cost_series(
            org_id=org_id,
            start_date=window_start,
            end_date=observed_date,
        )
        if not series_by_service:
            return CostAnomalyRunResult(
                observed_date=observed_date, scanned_services=0, detected=0, created=0, anomalies=[]
            )

        history_days = [window_start + timedelta(days=i) for i in range(lookback)]
        signals: list[CostAnomalySignal] = []
        for (provider, service), daily_costs in series_by_service.items():
            history_costs = [float(daily_costs.get(day, 0.0) or 0.0) for day in history_days]
            if len(history_costs) < history_min:
                continue
            current_cost = float(daily_costs.get(observed_date, 0.0) or 0.0)
            signal = detect_cost_anomaly_signal(
                provider=provider,
                service=service,
                observed_date=observed_date,
                current_cost_usd=current_cost,
                history_costs_usd=history_costs,
                z_threshold=threshold,
                min_delta_usd=delta_floor,
                window_days=lookback,
            )
            if signal:
                signals.append(signal)

        created_items: list[CostAnomaly] = []
        for signal in sorted(signals, key=lambda item: item.z_score, reverse=True):
            anomaly = await self._persist_signal(org_id=org_id, signal=signal)
            if anomaly is not None:
                created_items.append(anomaly)
                await self._maybe_emit_notification(org_id=org_id, anomaly=anomaly)

        return CostAnomalyRunResult(
            observed_date=observed_date,
            scanned_services=len(series_by_service),
            detected=len(signals),
            created=len(created_items),
            anomalies=created_items,
        )

    async def list_anomalies(
        self,
        *,
        org_id: UUID,
        provider: str | None = None,
        service: str | None = None,
        severity: CostAnomalySeverity | None = None,
        observed_from: date | None = None,
        observed_to: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CostAnomaly], int]:
        filters = [CostAnomaly.org_id == org_id]
        if provider:
            filters.append(CostAnomaly.provider == provider.lower())
        if service:
            filters.append(CostAnomaly.service == service)
        if severity:
            filters.append(CostAnomaly.severity == severity)
        if observed_from:
            filters.append(CostAnomaly.observed_date >= observed_from)
        if observed_to:
            filters.append(CostAnomaly.observed_date <= observed_to)

        total = (
            await self.db.execute(
                select(func.count()).select_from(CostAnomaly).where(and_(*filters))
            )
        ).scalar_one()

        rows = await self.db.execute(
            select(CostAnomaly)
            .where(and_(*filters))
            .order_by(CostAnomaly.observed_date.desc(), CostAnomaly.z_score.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total

    def _fetch_latest_cost_date(self, org_id: UUID) -> date | None:
        rows = execute_query(
            """
            SELECT max(date) AS max_date
            FROM cost_facts
            WHERE org_id = {org_id:String}
            """,
            {"org_id": str(org_id)},
        )
        if not rows:
            return None
        return _to_date(rows[0].get("max_date"))

    def _fetch_daily_cost_series(
        self,
        *,
        org_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[tuple[str, str], dict[date, float]]:
        rows = execute_query(
            """
            SELECT
              provider,
              service,
              date,
              sum(cost_usd) AS total_cost_usd
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {start:Date}
              AND date <= {end:Date}
            GROUP BY provider, service, date
            """,
            {"org_id": str(org_id), "start": start_date, "end": end_date},
        )

        series: dict[tuple[str, str], dict[date, float]] = {}
        for row in rows:
            day = _to_date(row.get("date"))
            if day is None:
                continue
            provider = str(row.get("provider") or "unknown").strip().lower()
            service = str(row.get("service") or "unknown").strip() or "unknown"
            key = (provider, service)
            series.setdefault(key, {})[day] = float(row.get("total_cost_usd") or 0.0)
        return series

    async def _persist_signal(self, *, org_id: UUID, signal: CostAnomalySignal) -> CostAnomaly | None:
        existing = await self.db.execute(
            select(CostAnomaly).where(
                CostAnomaly.org_id == org_id,
                CostAnomaly.provider == signal.provider,
                CostAnomaly.service == signal.service,
                CostAnomaly.observed_date == signal.observed_date,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None

        anomaly = CostAnomaly(
            org_id=org_id,
            provider=signal.provider,
            service=signal.service,
            observed_date=signal.observed_date,
            current_cost_usd=signal.current_cost_usd,
            historical_mean_usd=signal.historical_mean_usd,
            historical_stddev_usd=signal.historical_stddev_usd,
            z_score=signal.z_score,
            deviation_pct=signal.deviation_pct,
            severity=signal.severity,
            window_days=signal.window_days,
            z_threshold=signal.z_threshold,
            extra_metadata=None,
        )
        self.db.add(anomaly)
        await self.db.flush()
        await self.db.refresh(anomaly)
        return anomaly

    async def _maybe_emit_notification(self, *, org_id: UUID, anomaly: CostAnomaly) -> None:
        alert_severity = (
            AlertSeverity.CRITICAL
            if anomaly.severity == CostAnomalySeverity.HIGH
            else AlertSeverity.WARNING
        )
        pct_text = (
            f" ({anomaly.deviation_pct:.1f}% above mean)"
            if anomaly.deviation_pct is not None
            else ""
        )
        await NotificationsService(self.db).create_realtime_alert(
            org_id=org_id,
            category=AlertCategory.FINANCIAL,
            severity=alert_severity,
            event_type="cost.anomaly.detected",
            title=f"Cost anomaly detected in {anomaly.service}",
            body=(
                f"{anomaly.provider.upper()} {anomaly.service} is above baseline{pct_text}. "
                f"Current: ${anomaly.current_cost_usd:.2f}, "
                f"Mean({anomaly.window_days}d): ${anomaly.historical_mean_usd:.2f}, "
                f"z-score: {anomaly.z_score:.2f}."
            ),
            action_url="/app/economics/costs",
            source_type="cost_anomaly",
            source_id=f"{anomaly.observed_date.isoformat()}:{anomaly.provider}:{anomaly.service}",
            extra_metadata={
                "provider": anomaly.provider,
                "service": anomaly.service,
                "observed_date": anomaly.observed_date.isoformat(),
                "z_score": anomaly.z_score,
                "severity": anomaly.severity.value,
            },
        )
