from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domains.auth.models import Organization, User, UserRole
from app.workers.maintenance_worker import _run_user_retention_anonymization


async def _create_inactive_user(
    db,
    *,
    suffix: str,
    deleted_at: datetime,
    email: str | None = None,
) -> User:
    org = Organization(name=f"Retention Org {suffix}", slug=f"retention-org-{suffix}")
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        email=email or f"user-{suffix}@retention.example.com",
        full_name="Retention User",
        hashed_password="hashed",
        role=UserRole.VIEWER,
        is_active=False,
        deleted_at=deleted_at,
    )
    db.add(user)
    await db.commit()
    return user


@pytest.mark.asyncio
async def test_retention_policy_anonymizes_user_deleted_more_than_30_days(db):
    old_deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
    user = await _create_inactive_user(db, suffix=uuid4().hex[:8], deleted_at=old_deleted_at)
    original_email = user.email

    changed = await _run_user_retention_anonymization()
    assert changed >= 1

    db.expire_all()
    result = await db.execute(select(User).where(User.id == user.id))
    refreshed = result.scalar_one()
    assert refreshed.email != original_email
    assert refreshed.email.endswith("@deleted.invalid")
    assert refreshed.full_name == "Deleted User"


@pytest.mark.asyncio
async def test_retention_policy_keeps_recently_deleted_user_unchanged(db):
    recent_deleted_at = datetime.now(timezone.utc) - timedelta(days=7)
    user = await _create_inactive_user(db, suffix=uuid4().hex[:8], deleted_at=recent_deleted_at)
    original_email = user.email
    original_name = user.full_name

    changed = await _run_user_retention_anonymization()
    assert changed == 0

    db.expire_all()
    result = await db.execute(select(User).where(User.id == user.id))
    refreshed = result.scalar_one()
    assert refreshed.email == original_email
    assert refreshed.full_name == original_name
