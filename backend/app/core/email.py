from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


class EmailService:
    """SMTP sender with safe no-op fallback when not configured."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        if not self.settings.smtp_enabled:
            return False
        return bool(self.settings.smtp_host and self.settings.smtp_from_email)

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> bool:
        if not self.enabled:
            log.info("email.skipped.disabled", to=to_email, subject=subject)
            return False

        msg = EmailMessage()
        from_name = self.settings.smtp_from_name.strip()
        if from_name:
            msg["From"] = f"{from_name} <{self.settings.smtp_from_email}>"
        else:
            msg["From"] = self.settings.smtp_from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        try:
            await asyncio.to_thread(self._send_sync, msg)
            log.info("email.sent", to=to_email, subject=subject)
            return True
        except Exception as exc:
            log.error("email.send_failed", to=to_email, subject=subject, error=str(exc))
            return False

    async def send_critical_alert(
        self,
        *,
        subject: str,
        text_body: str,
    ) -> int:
        """Send an operational critical alert to configured recipients."""
        recipients = self.settings.smtp_alert_to_list
        if not recipients:
            log.info("email.alert.skipped.no_recipients", subject=subject)
            return 0

        sent = 0
        for to_email in recipients:
            ok = await self.send_email(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
            )
            if ok:
                sent += 1
        return sent

    def _send_sync(self, msg: EmailMessage) -> None:
        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=self.settings.smtp_timeout_seconds,
            ) as smtp:
                if self.settings.smtp_username:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=self.settings.smtp_timeout_seconds,
        ) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(msg)
