"""Minimal operational alerting module (SP-OP-ALERT).

Provides a single entry point — send_alert() — for critical operational events.
Current implementation: structured log + optional SMTP email to ops team.
Future: wire to PagerDuty, OpsGenie, or Slack incident channels.

Design principles:
  - Fire-and-forget: alerting failures must never crash the caller.
  - Severity-based: only CRITICAL and HIGH trigger email; all severities log.
  - Idempotent-safe: callers may invoke repeatedly without deduplication concern
    (deduplication is the responsibility of the downstream alerting platform).
"""
from __future__ import annotations

import enum
from typing import Optional

from app.core.logging import get_logger

log = get_logger("alerting")


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def send_alert(
    *,
    subject: str,
    body: str,
    severity: AlertSeverity = AlertSeverity.HIGH,
    source: str = "unknown",
    context: Optional[dict] = None,
) -> None:
    """Emit an operational alert.

    Args:
        subject: Short summary (suitable for email subject / incident title).
        body: Detailed description of the issue and recommended action.
        severity: Alert severity level.
        source: Subsystem that triggered the alert (e.g. "worker.ingestion").
        context: Optional structured metadata for downstream systems.
    """
    # Always log — this is the baseline that works everywhere.
    log.warning(
        "ops.alert",
        alert_subject=subject,
        alert_severity=severity.value,
        alert_source=source,
        alert_body=body[:500],
        **(context or {}),
    )

    # Email notification for CRITICAL and HIGH severity
    if severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH):
        _try_send_email_alert(subject=subject, body=body, severity=severity, source=source)


def _try_send_email_alert(
    *,
    subject: str,
    body: str,
    severity: AlertSeverity,
    source: str,
) -> None:
    """Best-effort email alert to the ops team. Never raises.

    Uses asyncio to schedule the email send if an event loop is running.
    Falls back to log-only if no loop is available or SMTP is not configured.
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.smtp_enabled or not settings.smtp_alert_to_list:
            return

        import asyncio

        from app.core.email import EmailService

        full_subject = f"[CauSium {severity.value.upper()}] {subject}"
        html_body = (
            f"<h3>{subject}</h3>"
            f"<p><strong>Severity:</strong> {severity.value}</p>"
            f"<p><strong>Source:</strong> {source}</p>"
            f"<pre>{body}</pre>"
            f"<hr><p><em>CauSium Operational Alerting</em></p>"
        )

        async def _send():
            email_service = EmailService()
            await email_service.send_email(
                to=settings.smtp_alert_to_list,
                subject=full_subject,
                html_body=html_body,
            )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_send())
        except RuntimeError:
            # No running event loop — skip email, log is sufficient
            pass
    except Exception:
        # Alerting must never crash the caller
        log.error("ops.alert.email_failed", subject=subject, source=source, exc_info=True)
