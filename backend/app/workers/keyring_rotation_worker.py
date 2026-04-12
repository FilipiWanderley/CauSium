from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.core.security import rotate_expired_workspace_keyrings

log = get_logger(__name__)


async def run_keyring_rotation_worker() -> None:
    settings = get_settings()
    interval_seconds = max(60, settings.workspace_key_rotation_interval_minutes * 60)
    max_age_days = max(1, settings.workspace_key_max_age_days)
    batch_size = max(1, settings.workspace_key_rotation_batch_size)

    log.info(
        "keyring_rotation_worker.started",
        interval_seconds=interval_seconds,
        max_age_days=max_age_days,
        batch_size=batch_size,
    )

    while True:
        try:
            async with async_session_factory() as db:
                stats = await rotate_expired_workspace_keyrings(
                    db,
                    max_age_days=max_age_days,
                    batch_size=batch_size,
                )
                await db.commit()
                log.info("keyring_rotation_worker.tick", **stats)
        except Exception as e:
            log.error("keyring_rotation_worker.error", error=str(e))

        await asyncio.sleep(interval_seconds)