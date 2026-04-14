from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import decrypt_secret_for_org
from app.domains.notifications.models import NotificationSlackConfig

log = get_logger(__name__)


class SlackService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def send_critical_alert(self, *, org_id, subject: str, text_body: str) -> bool:
        if org_id is None:
            return False

        result = await self.db.execute(
            select(NotificationSlackConfig).where(NotificationSlackConfig.org_id == org_id)
        )
        cfg = result.scalar_one_or_none()
        if cfg is None or not cfg.enabled or not cfg.webhook_encrypted:
            return False

        try:
            webhook_url = await decrypt_secret_for_org(self.db, cfg.org_id, cfg.webhook_encrypted)
        except Exception as exc:
            log.error("slack.decrypt_failed", org_id=str(org_id), error=str(exc))
            return False

        payload = {
            "text": (
                ":rotating_light: *CauSium Critical Alert*\n"
                f"*Subject:* {subject}\n\n"
                f"{text_body.strip()}"
            )
        }

        timeout = httpx.Timeout(self.settings.smtp_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 300:
                log.error(
                    "slack.send_failed",
                    org_id=str(org_id),
                    status_code=resp.status_code,
                    body=resp.text,
                )
                return False
            return True
        except Exception as exc:
            log.error("slack.send_exception", org_id=str(org_id), error=str(exc))
            return False
