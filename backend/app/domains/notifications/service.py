from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import encrypt_secret_for_org
from app.domains.notifications.models import (
    ActivityEvent,
    ActivityEventSeverity,
    AlertCategory,
    AlertRecord,
    NotificationAlertRule,
    NotificationPreference,
    NotificationFrequency,
    NotificationSlackConfig,
    AlertSeverity,
    AlertStatus,
)
from app.domains.notifications.realtime import notifications_realtime_broker

log = get_logger(__name__)

_SEVERITY_RANK = {
    AlertSeverity.INFO: 1,
    AlertSeverity.WARNING: 2,
    AlertSeverity.CRITICAL: 3,
}

_ACTIVITY_TO_ALERT_SEVERITY = {
    ActivityEventSeverity.INFO: AlertSeverity.INFO,
    ActivityEventSeverity.WARNING: AlertSeverity.WARNING,
    ActivityEventSeverity.CRITICAL: AlertSeverity.CRITICAL,
}

_SYNC_DEDUPE_EVENT_TYPES = {
    "cloud_account.sync.completed",
    "cloud_account.sync.warning",
}
_SYNC_DEDUPE_WINDOW_MINUTES = 30
_ANOMALY_DEDUPE_EVENT_TYPES = {"cost.anomaly.detected"}
_BUDGET_DEDUPE_EVENT_TYPES = {"budget.threshold.crossed"}


class NotificationsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list(
        self,
        org_id: UUID,
        user_id: Optional[UUID] = None,
        category: Optional[AlertCategory] = None,
        status: Optional[AlertStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AlertRecord], int]:
        """Return alerts visible to a user (workspace-wide + user-scoped)."""
        scope_filter = or_(
            AlertRecord.user_id.is_(None),
            AlertRecord.user_id == user_id,
        ) if user_id else AlertRecord.user_id.is_(None)

        filters = [AlertRecord.org_id == org_id, scope_filter]
        if category:
            filters.append(AlertRecord.category == category)
        if status:
            filters.append(AlertRecord.status == status)
        else:
            # Default: exclude archived
            filters.append(AlertRecord.status != AlertStatus.ARCHIVED)

        count_q = select(func.count()).select_from(AlertRecord).where(and_(*filters))
        total = (await self.db.execute(count_q)).scalar_one()

        items_result = await self.db.execute(
            select(AlertRecord)
            .where(and_(*filters))
            .order_by(AlertRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def unread_count(
        self,
        org_id: UUID,
        user_id: Optional[UUID] = None,
        category: Optional[AlertCategory] = None,
    ) -> dict:
        scope_filter = or_(
            AlertRecord.user_id.is_(None),
            AlertRecord.user_id == user_id,
        ) if user_id else AlertRecord.user_id.is_(None)

        base = [
            AlertRecord.org_id == org_id,
            AlertRecord.status == AlertStatus.UNREAD,
            scope_filter,
        ]

        if category:
            base.append(AlertRecord.category == category)

        total_r = await self.db.execute(
            select(func.count()).select_from(AlertRecord).where(and_(*base))
        )
        critical_r = await self.db.execute(
            select(func.count())
            .select_from(AlertRecord)
            .where(and_(*base, AlertRecord.severity == AlertSeverity.CRITICAL))
        )
        return {
            "unread": total_r.scalar_one(),
            "critical": critical_r.scalar_one(),
        }

    async def get(self, org_id: UUID, alert_id: UUID) -> Optional[AlertRecord]:
        result = await self.db.execute(
            select(AlertRecord).where(
                AlertRecord.id == alert_id, AlertRecord.org_id == org_id
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def set_status(
        self, org_id: UUID, alert_id: UUID, new_status: AlertStatus
    ) -> Optional[AlertRecord]:
        alert = await self.get(org_id, alert_id)
        if not alert:
            return None

        now = datetime.now(tz=timezone.utc)
        alert.status = new_status
        if new_status == AlertStatus.READ and alert.read_at is None:
            alert.read_at = now
        elif new_status == AlertStatus.ARCHIVED:
            alert.archived_at = now

        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def mark_all_read(self, org_id: UUID, user_id: Optional[UUID] = None) -> int:
        """Mark all unread alerts as read. Returns affected count."""
        scope_filter = or_(
            AlertRecord.user_id.is_(None),
            AlertRecord.user_id == user_id,
        ) if user_id else AlertRecord.user_id.is_(None)

        result = await self.db.execute(
            select(AlertRecord).where(
                and_(
                    AlertRecord.org_id == org_id,
                    AlertRecord.status == AlertStatus.UNREAD,
                    scope_filter,
                )
            )
        )
        alerts = list(result.scalars().all())
        now = datetime.now(tz=timezone.utc)
        for alert in alerts:
            alert.status = AlertStatus.READ
            if alert.read_at is None:
                alert.read_at = now

        await self.db.flush()
        return len(alerts)

    # ------------------------------------------------------------------
    # Internal: create
    # ------------------------------------------------------------------

    async def create(
        self,
        org_id: UUID,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        body: Optional[str] = None,
        action_url: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        extra_metadata: Optional[dict] = None,
    ) -> AlertRecord:
        alert = AlertRecord(
            org_id=org_id,
            user_id=user_id,
            category=category,
            severity=severity,
            title=title,
            body=body,
            action_url=action_url,
            source_type=source_type,
            source_id=source_id,
            extra_metadata=extra_metadata,
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        await notifications_realtime_broker.publish(
            org_id,
            {
                "type": "notification.created",
                "notification": {
                    "id": str(alert.id),
                    "org_id": str(alert.org_id),
                    "category": alert.category.value,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "title": alert.title,
                    "created_at": alert.created_at.isoformat(),
                },
            },
        )
        return alert

    async def _get_alert_by_source(
        self,
        *,
        org_id: UUID,
        category: AlertCategory,
        source_type: str,
        source_id: str,
    ) -> AlertRecord | None:
        result = await self.db.execute(
            select(AlertRecord).where(
                AlertRecord.org_id == org_id,
                AlertRecord.category == category,
                AlertRecord.source_type == source_type,
                AlertRecord.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _extract_sync_account_id(
        *,
        source_id: str | None,
        extra_metadata: dict | None,
    ) -> str | None:
        if isinstance(extra_metadata, dict):
            raw_account_id = extra_metadata.get("account_id")
            if raw_account_id:
                try:
                    return str(UUID(str(raw_account_id)))
                except (TypeError, ValueError):
                    pass

        if source_id:
            # Expected sync source_id patterns:
            # - "{account_id}:{start_iso}:{end_iso}"
            # - "{account_id}:{lookback_days}:inline"
            first_token = str(source_id).split(":", 1)[0]
            if first_token:
                try:
                    return str(UUID(first_token))
                except (TypeError, ValueError):
                    pass
        return None

    async def _get_recent_sync_equivalent_alert(
        self,
        *,
        org_id: UUID,
        event_type: str,
        account_id: str,
    ) -> AlertRecord | None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_SYNC_DEDUPE_WINDOW_MINUTES)
        result = await self.db.execute(
            select(AlertRecord)
            .where(
                AlertRecord.org_id == org_id,
                AlertRecord.created_at >= cutoff,
                AlertRecord.extra_metadata["event_type"].astext == event_type,
                AlertRecord.extra_metadata["account_id"].astext == account_id,
            )
            .order_by(AlertRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _normalize_observed_date(value: object) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if "T" in text:
            text = text.split("T", 1)[0]
        return text

    @staticmethod
    def _extract_anomaly_signature(
        *,
        source_id: str | None,
        extra_metadata: dict | None,
    ) -> dict[str, str] | None:
        provider: str | None = None
        service: str | None = None
        observed_date: str | None = None

        if isinstance(extra_metadata, dict):
            provider_raw = str(extra_metadata.get("provider") or "").strip().lower()
            service_raw = str(extra_metadata.get("service") or "").strip().lower()
            observed_date_raw = NotificationsService._normalize_observed_date(
                extra_metadata.get("observed_date")
            )
            provider = provider_raw or None
            service = service_raw or None
            observed_date = observed_date_raw or None

        # Fallback for legacy payloads where metadata may be incomplete.
        if (not provider or not service or not observed_date) and source_id:
            parts = str(source_id).split(":", 2)
            if len(parts) == 3:
                fallback_date = NotificationsService._normalize_observed_date(parts[0])
                fallback_provider = parts[1].strip().lower() or None
                fallback_service = parts[2].strip().lower() or None
                provider = provider or fallback_provider
                service = service or fallback_service
                observed_date = observed_date or fallback_date

        if not provider or not service or not observed_date:
            return None
        return {
            "provider": provider,
            "service": service,
            "observed_date": observed_date,
        }

    @staticmethod
    def _extract_budget_signature(
        *,
        source_id: str | None,
        extra_metadata: dict | None,
    ) -> dict[str, str] | None:
        budget_id: str | None = None
        period_start: str | None = None
        threshold: str | None = None

        # Primary source for budget dedupe is source_id.
        if source_id:
            parts = str(source_id).split(":", 2)
            if len(parts) == 3:
                budget_id = parts[0].strip() or None
                period_start = NotificationsService._normalize_observed_date(parts[1])
                threshold_raw = parts[2].strip()
                # Source may carry an additional suffix after threshold;
                # keep only the first segment for semantic dedupe.
                threshold_raw = threshold_raw.split(":", 1)[0].strip()
                threshold = str(int(threshold_raw)) if threshold_raw.isdigit() else (threshold_raw or None)

        # Fallback for callers that only provide metadata.
        if isinstance(extra_metadata, dict):
            if not budget_id:
                budget_raw = str(extra_metadata.get("budget_id") or "").strip()
                budget_id = budget_raw or None
            if not period_start:
                period_start = NotificationsService._normalize_observed_date(
                    extra_metadata.get("period_start")
                )
            if not threshold:
                threshold_value = extra_metadata.get("threshold")
                if threshold_value is not None:
                    try:
                        threshold = str(int(threshold_value))
                    except (TypeError, ValueError):
                        threshold = str(threshold_value).strip() or None

        if not budget_id or not period_start or not threshold:
            return None
        return {
            "budget_id": budget_id,
            "period_start": period_start,
            "threshold": threshold,
        }

    async def _get_semantic_equivalent_alert(
        self,
        *,
        org_id: UUID,
        category: AlertCategory,
        event_type: str,
        signature: dict[str, str],
    ) -> AlertRecord | None:
        filters = [
            AlertRecord.org_id == org_id,
            AlertRecord.category == category,
            AlertRecord.extra_metadata["event_type"].astext == event_type,
        ]
        for key, value in signature.items():
            filters.append(AlertRecord.extra_metadata[key].astext == value)

        result = await self.db.execute(
            select(AlertRecord)
            .where(and_(*filters))
            .order_by(AlertRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Notification preferences (SP-NT03)
    # ------------------------------------------------------------------

    async def get_preference(self, org_id: UUID, user_id: UUID) -> NotificationPreference:
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.org_id == org_id,
                NotificationPreference.user_id == user_id,
            )
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            pref = NotificationPreference(
                org_id=org_id,
                user_id=user_id,
                in_app_enabled=True,
                email_enabled=True,
                slack_enabled=False,
                frequency=NotificationFrequency.INSTANT,
                categories={
                    "financial": True,
                    "optimization": True,
                    "governance": True,
                    "activity": True,
                    "security": True,
                },
            )
            self.db.add(pref)
            await self.db.flush()
            await self.db.refresh(pref)
        return pref

    async def upsert_preference(
        self,
        org_id: UUID,
        user_id: UUID,
        *,
        in_app_enabled: bool | None = None,
        email_enabled: bool | None = None,
        slack_enabled: bool | None = None,
        frequency: NotificationFrequency | None = None,
        categories: dict | None = None,
    ) -> NotificationPreference:
        pref = await self.get_preference(org_id, user_id)

        if in_app_enabled is not None:
            pref.in_app_enabled = in_app_enabled
        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if slack_enabled is not None:
            pref.slack_enabled = slack_enabled
        if frequency is not None:
            pref.frequency = frequency
        if categories is not None:
            pref.categories = categories

        await self.db.flush()
        await self.db.refresh(pref)
        return pref

    async def get_slack_config(self, org_id: UUID) -> NotificationSlackConfig:
        result = await self.db.execute(
            select(NotificationSlackConfig).where(NotificationSlackConfig.org_id == org_id)
        )
        cfg = result.scalar_one_or_none()
        if cfg is None:
            cfg = NotificationSlackConfig(
                org_id=org_id,
                enabled=False,
                webhook_encrypted=None,
            )
            self.db.add(cfg)
            await self.db.flush()
            await self.db.refresh(cfg)
        return cfg

    async def upsert_slack_config(
        self,
        org_id: UUID,
        *,
        enabled: bool | None = None,
        webhook_url: str | None = None,
    ) -> NotificationSlackConfig:
        cfg = await self.get_slack_config(org_id)
        if enabled is not None:
            cfg.enabled = enabled

        if webhook_url is not None:
            normalized = webhook_url.strip()
            if normalized and not normalized.startswith("https://hooks.slack.com/"):
                raise ValueError("Invalid Slack webhook URL")
            cfg.webhook_encrypted = (
                await encrypt_secret_for_org(self.db, org_id, normalized) if normalized else None
            )

        await self.db.flush()
        await self.db.refresh(cfg)
        return cfg

    async def get_alert_rule(self, org_id: UUID, category: AlertCategory) -> NotificationAlertRule:
        result = await self.db.execute(
            select(NotificationAlertRule).where(
                NotificationAlertRule.org_id == org_id,
                NotificationAlertRule.category == category,
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            rule = NotificationAlertRule(
                org_id=org_id,
                category=category,
                enabled=True,
                min_severity=AlertSeverity.CRITICAL,
                event_type_prefix=None,
            )
            self.db.add(rule)
            await self.db.flush()
            await self.db.refresh(rule)
        return rule

    async def upsert_alert_rule(
        self,
        org_id: UUID,
        category: AlertCategory,
        *,
        enabled: bool | None = None,
        min_severity: AlertSeverity | None = None,
        event_type_prefix: str | None = None,
    ) -> NotificationAlertRule:
        rule = await self.get_alert_rule(org_id, category)

        if enabled is not None:
            rule.enabled = enabled
        if min_severity is not None:
            rule.min_severity = min_severity
        if event_type_prefix is not None:
            normalized = event_type_prefix.strip()
            rule.event_type_prefix = normalized or None

        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def should_create_alert(
        self,
        *,
        org_id: UUID,
        category: AlertCategory,
        event_type: str,
        severity: AlertSeverity,
    ) -> bool:
        rule = await self.get_alert_rule(org_id, category)
        if not rule.enabled:
            return False

        if _SEVERITY_RANK[severity] < _SEVERITY_RANK[rule.min_severity]:
            return False

        if rule.event_type_prefix and not event_type.startswith(rule.event_type_prefix):
            return False

        return True

    async def create_if_rule_matches(
        self,
        *,
        org_id: UUID,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        body: str | None = None,
        action_url: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        user_id: UUID | None = None,
        extra_metadata: dict | None = None,
        event_type: str,
        ignore_rules: bool = False,
    ) -> AlertRecord | None:
        if not ignore_rules:
            if not await self.should_create_alert(
                org_id=org_id,
                category=category,
                event_type=event_type,
                severity=severity,
            ):
                return None

        if source_type and source_id:
            existing = await self._get_alert_by_source(
                org_id=org_id,
                category=category,
                source_type=source_type,
                source_id=source_id,
            )
            if existing is not None:
                return existing

        normalized_metadata: dict = dict(extra_metadata) if isinstance(extra_metadata, dict) else {}
        if event_type in _SYNC_DEDUPE_EVENT_TYPES:
            account_id = self._extract_sync_account_id(
                source_id=source_id,
                extra_metadata=normalized_metadata,
            )
            normalized_metadata["event_type"] = event_type
            if account_id:
                normalized_metadata["account_id"] = account_id
                recent_equivalent = await self._get_recent_sync_equivalent_alert(
                    org_id=org_id,
                    event_type=event_type,
                    account_id=account_id,
                )
                if recent_equivalent is not None:
                    return recent_equivalent
        elif event_type in _ANOMALY_DEDUPE_EVENT_TYPES:
            anomaly_signature = self._extract_anomaly_signature(
                source_id=source_id,
                extra_metadata=normalized_metadata,
            )
            normalized_metadata["event_type"] = event_type
            if anomaly_signature:
                normalized_metadata.update(anomaly_signature)
                equivalent = await self._get_semantic_equivalent_alert(
                    org_id=org_id,
                    category=category,
                    event_type=event_type,
                    signature=anomaly_signature,
                )
                if equivalent is not None:
                    return equivalent
        elif event_type in _BUDGET_DEDUPE_EVENT_TYPES:
            budget_signature = self._extract_budget_signature(
                source_id=source_id,
                extra_metadata=normalized_metadata,
            )
            normalized_metadata["event_type"] = event_type
            if budget_signature:
                normalized_metadata.update(budget_signature)
                equivalent = await self._get_semantic_equivalent_alert(
                    org_id=org_id,
                    category=category,
                    event_type=event_type,
                    signature=budget_signature,
                )
                if equivalent is not None:
                    return equivalent

        return await self.create(
            org_id=org_id,
            category=category,
            severity=severity,
            title=title,
            body=body,
            action_url=action_url,
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
            extra_metadata=normalized_metadata or None,
        )

    async def create_realtime_alert(
        self,
        *,
        org_id: UUID,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        body: str | None = None,
        action_url: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        user_id: UUID | None = None,
        extra_metadata: dict | None = None,
        event_type: str,
    ) -> AlertRecord | None:
        """Create an alert immediately, bypassing per-org notification rules."""
        return await self.create_if_rule_matches(
            org_id=org_id,
            category=category,
            severity=severity,
            title=title,
            body=body,
            action_url=action_url,
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
            extra_metadata=extra_metadata,
            event_type=event_type,
            ignore_rules=True,
        )

    # ------------------------------------------------------------------
    # Activity events (SP-NT01)
    # ------------------------------------------------------------------

    async def create_activity_event(
        self,
        *,
        org_id: UUID,
        provider: str,
        event_type: str,
        title: str,
        occurred_at: datetime,
        severity: ActivityEventSeverity = ActivityEventSeverity.INFO,
        body: str | None = None,
        service: str | None = None,
        resource_id: str | None = None,
        account_id: UUID | None = None,
        extra_metadata: dict | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            org_id=org_id,
            account_id=account_id,
            provider=provider,
            event_type=event_type,
            severity=severity,
            service=service,
            resource_id=resource_id,
            title=title,
            body=body,
            extra_metadata=extra_metadata,
            occurred_at=occurred_at,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        mapped_severity = _ACTIVITY_TO_ALERT_SEVERITY[severity]
        await self.create_realtime_alert(
            org_id=org_id,
            category=AlertCategory.ACTIVITY,
            severity=mapped_severity,
            event_type=event_type,
            title=f"Activity event: {event_type}",
            body=title,
            source_type="activity_event",
            source_id=str(event.id),
            extra_metadata={"provider": provider, "service": service, "resource_id": resource_id},
        )

        return event

    async def list_activity_events(
        self,
        *,
        org_id: UUID,
        event_type: str | None = None,
        resource_id: str | None = None,
        service: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ActivityEvent], int]:
        filters = [ActivityEvent.org_id == org_id]
        if event_type:
            filters.append(ActivityEvent.event_type == event_type)
        if resource_id:
            filters.append(ActivityEvent.resource_id == resource_id)
        if service:
            filters.append(ActivityEvent.service == service)
        if occurred_from:
            filters.append(ActivityEvent.occurred_at >= occurred_from)
        if occurred_to:
            filters.append(ActivityEvent.occurred_at <= occurred_to)

        total = (
            await self.db.execute(
                select(func.count()).select_from(ActivityEvent).where(and_(*filters))
            )
        ).scalar_one()

        rows = await self.db.execute(
            select(ActivityEvent)
            .where(and_(*filters))
            .order_by(ActivityEvent.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total
