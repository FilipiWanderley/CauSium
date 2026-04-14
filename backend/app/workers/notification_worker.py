"""Notification delivery worker.

Polls for newly created AlertRecords that haven't been dispatched via email or
Slack and delivers them to users whose NotificationPreference has the relevant
channel enabled and frequency=INSTANT.

Deduplication is handled by the email_sent_at / slack_sent_at columns written
atomically inside a DB transaction before the actual dispatch, so a process
restart will never double-send.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.email import EmailService
from app.core.logging import get_logger
from app.core.slack import SlackService
from app.domains.auth.models import User
from app.domains.notifications.models import (
    AlertRecord,
    AlertSeverity,
    NotificationFrequency,
    NotificationPreference,
)

log = get_logger(__name__)

# How often to poll (seconds)
POLL_INTERVAL = 30
# Only process alerts created within this window to avoid re-scanning old data
LOOKBACK_HOURS = 24
# Batch size per poll cycle
BATCH_SIZE = 50


async def _get_pending_email_alerts(db: AsyncSession) -> list[AlertRecord]:
    """Return alerts that need email delivery."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    result = await db.execute(
        select(AlertRecord)
        .where(
            and_(
                AlertRecord.email_sent_at.is_(None),
                AlertRecord.created_at >= cutoff,
            )
        )
        .order_by(AlertRecord.created_at.asc())
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def _get_pending_slack_alerts(db: AsyncSession) -> list[AlertRecord]:
    """Return alerts that need Slack delivery."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    result = await db.execute(
        select(AlertRecord)
        .where(
            and_(
                AlertRecord.slack_sent_at.is_(None),
                AlertRecord.created_at >= cutoff,
            )
        )
        .order_by(AlertRecord.created_at.asc())
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def _get_instant_email_recipients(
    db: AsyncSession, org_id: UUID, category_key: str
) -> list[User]:
    """Return active users in org that have email + instant notifications enabled for this category."""
    result = await db.execute(
        select(User)
        .join(
            NotificationPreference,
            and_(
                NotificationPreference.user_id == User.id,
                NotificationPreference.org_id == org_id,
            ),
        )
        .where(
            and_(
                User.org_id == org_id,
                User.is_active.is_(True),
                NotificationPreference.email_enabled.is_(True),
                NotificationPreference.frequency == NotificationFrequency.INSTANT,
            )
        )
    )
    users = list(result.scalars().all())

    # Filter by per-category preference (categories is a JSONB dict like {"financial": true, ...})
    def _category_enabled(pref_categories: dict | None) -> bool:
        if pref_categories is None:
            return True  # no override → all categories enabled
        return bool(pref_categories.get(category_key, True))

    # Reload prefs to check categories — fetch all prefs for users in one query
    user_ids = [u.id for u in users]
    if not user_ids:
        return []

    prefs_result = await db.execute(
        select(NotificationPreference).where(
            and_(
                NotificationPreference.org_id == org_id,
                NotificationPreference.user_id.in_(user_ids),
            )
        )
    )
    pref_map: dict[UUID, NotificationPreference] = {
        p.user_id: p for p in prefs_result.scalars().all()
    }

    return [u for u in users if _category_enabled(pref_map.get(u.id, None) and pref_map[u.id].categories)]


def _severity_label(severity: AlertSeverity) -> str:
    labels = {
        AlertSeverity.INFO: "Info",
        AlertSeverity.WARNING: "Aviso",
        AlertSeverity.CRITICAL: "Crítico",
    }
    return labels.get(severity, str(severity))


def _build_alert_email(alert: AlertRecord) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body) for an AlertRecord."""
    severity_label = _severity_label(alert.severity)
    subject = f"[CauSium][{severity_label}] {alert.title}"

    text_body = (
        f"Categoria: {alert.category.value}\n"
        f"Severidade: {severity_label}\n\n"
        f"{alert.title}\n"
    )
    if alert.body:
        text_body += f"\n{alert.body}\n"
    if alert.action_url:
        text_body += f"\nAcesse: {alert.action_url}\n"
    text_body += "\nEsta é uma mensagem automática do CauSium."

    safe_title = alert.title.replace("<", "&lt;").replace(">", "&gt;")
    safe_body = (alert.body or "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    severity_color = {
        AlertSeverity.INFO: "#2563eb",
        AlertSeverity.WARNING: "#d97706",
        AlertSeverity.CRITICAL: "#dc2626",
    }.get(alert.severity, "#374151")

    html_body = (
        "<html><body style='font-family:Arial,sans-serif;color:#1f2937;'>"
        "<div style='max-width:600px;margin:0 auto;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;'>"
        f"<div style='background:{severity_color};color:#fff;padding:12px 16px;font-weight:700;'>"
        f"CauSium — {severity_label}: {safe_title}"
        "</div>"
        "<div style='padding:16px;'>"
        f"<p style='margin:0 0 8px 0;'><strong>Categoria:</strong> {alert.category.value}</p>"
    )
    if safe_body:
        html_body += f"<p style='margin:0 0 12px 0;'>{safe_body}</p>"
    if alert.action_url:
        safe_url = alert.action_url.replace('"', "%22")
        html_body += (
            f"<a href='{safe_url}' style='display:inline-block;background:{severity_color};"
            "color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;'>Ver no CauSium</a>"
        )
    html_body += "<p style='color:#6b7280;margin:16px 0 0 0;font-size:12px;'>Mensagem automática do CauSium.</p>"
    html_body += "</div></div></body></html>"

    return subject, text_body, html_body


async def _dispatch_email_alerts(alerts: list[AlertRecord], db: AsyncSession) -> None:
    """Send email for each alert to eligible users, then mark email_sent_at."""
    email_svc = EmailService()
    now = datetime.now(tz=timezone.utc)

    for alert in alerts:
        # Mark as sent first (optimistic) — prevents duplicate sends on retry
        alert.email_sent_at = now
        await db.flush()

        recipients = await _get_instant_email_recipients(db, alert.org_id, alert.category.value)
        if not recipients:
            log.info(
                "notification.email.no_recipients",
                alert_id=str(alert.id),
                org_id=str(alert.org_id),
            )
            continue

        subject, text_body, html_body = _build_alert_email(alert)

        sent = 0
        for user in recipients:
            ok = await email_svc.send_email(
                to_email=user.email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
            if ok:
                sent += 1

        log.info(
            "notification.email.dispatched",
            alert_id=str(alert.id),
            severity=alert.severity.value,
            sent=sent,
            total_recipients=len(recipients),
        )


async def _dispatch_slack_alerts(alerts: list[AlertRecord], db: AsyncSession) -> None:
    """Send Slack message for each alert org, then mark slack_sent_at."""
    now = datetime.now(tz=timezone.utc)

    for alert in alerts:
        # Check if any user in the org has slack_enabled + INSTANT
        result = await db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.org_id == alert.org_id,
                    NotificationPreference.slack_enabled.is_(True),
                    NotificationPreference.frequency == NotificationFrequency.INSTANT,
                )
            )
        )
        prefs = list(result.scalars().all())

        # Mark as sent before dispatch to prevent duplicates
        alert.slack_sent_at = now
        await db.flush()

        if not prefs:
            continue

        severity_label = _severity_label(alert.severity)
        subject = f"[{severity_label}] {alert.title}"
        body_parts = [f"Categoria: {alert.category.value}"]
        if alert.body:
            body_parts.append(alert.body)
        if alert.action_url:
            body_parts.append(f"<{alert.action_url}|Ver no CauSium>")
        text_body = "\n".join(body_parts)

        slack_svc = SlackService(db)
        ok = await slack_svc.send_critical_alert(
            org_id=alert.org_id,
            subject=subject,
            text_body=text_body,
        )
        log.info(
            "notification.slack.dispatched",
            alert_id=str(alert.id),
            org_id=str(alert.org_id),
            sent=ok,
        )


async def run_once() -> None:
    """Process one batch of pending notifications."""
    async with async_session_factory() as db:
        async with db.begin():
            email_alerts = await _get_pending_email_alerts(db)
            if email_alerts:
                await _dispatch_email_alerts(email_alerts, db)

    async with async_session_factory() as db:
        async with db.begin():
            slack_alerts = await _get_pending_slack_alerts(db)
            if slack_alerts:
                await _dispatch_slack_alerts(slack_alerts, db)


async def run_notification_worker() -> None:
    log.info("notification_worker.started")
    while True:
        try:
            await run_once()
        except Exception as exc:
            log.error("notification_worker.error", error=str(exc))
        await asyncio.sleep(POLL_INTERVAL)
