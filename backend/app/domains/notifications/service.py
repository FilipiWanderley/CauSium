from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.notifications.models import (
    AlertCategory,
    AlertRecord,
    NotificationPreference,
    NotificationFrequency,
    AlertSeverity,
    AlertStatus,
)

log = get_logger(__name__)


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
        return alert

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
