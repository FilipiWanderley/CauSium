from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.settings.models import TenantSetting


class TenantSettingsService:
    """Service for managing per-tenant settings (async)."""

    DEFAULT_MONITORED_TAG_KEY = "team"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_setting(self, org_id: UUID, key: str, default: str | None = None) -> str | None:
        """Get a setting value for a tenant, or return default if not found."""
        result = await self.db.execute(
            select(TenantSetting).where(
                TenantSetting.org_id == org_id,
                TenantSetting.setting_key == key,
            )
        )
        row = result.scalar_one_or_none()
        return row.setting_value if row else default

    async def set_setting(self, org_id: UUID, key: str, value: str) -> TenantSetting:
        """Set a setting value for a tenant (upsert)."""
        result = await self.db.execute(
            select(TenantSetting).where(
                TenantSetting.org_id == org_id,
                TenantSetting.setting_key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.setting_value = value
            self.db.add(existing)
            await self.db.flush()
            return existing

        new_setting = TenantSetting(
            org_id=org_id,
            setting_key=key,
            setting_value=value,
        )
        self.db.add(new_setting)
        await self.db.flush()
        return new_setting

    async def get_monitored_tag_key(self, org_id: UUID) -> str:
        """Get the monitored tag key for a tenant, with system default."""
        value = await self.get_setting(org_id, "monitored_tag_key", self.DEFAULT_MONITORED_TAG_KEY)
        return value if value is not None else self.DEFAULT_MONITORED_TAG_KEY

    async def set_monitored_tag_key(self, org_id: UUID, value: str) -> TenantSetting:
        """Set the monitored tag key for a tenant."""
        return await self.set_setting(org_id, "monitored_tag_key", value)