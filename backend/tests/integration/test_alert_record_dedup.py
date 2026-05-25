import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.domains.notifications.models import AlertCategory, AlertRecord, AlertSeverity
from app.domains.notifications.service import NotificationsService


@pytest.mark.asyncio
async def test_alert_records_dedupe_under_concurrent_creators(client, session_factory):
    suffix = uuid4().hex[:8]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Dedupe Org",
            "org_slug": f"dedupe-org-{suffix}",
            "email": f"dedupe-{suffix}@example.com",
            "full_name": "Dedupe Admin",
            "password": "testpassword123",
        },
    )
    assert resp.status_code == 201, resp.text
    org_id = UUID(resp.json()["user"]["org_id"])

    async def _create() -> UUID:
        async with session_factory() as db:
            svc = NotificationsService(db)
            alert = await svc.create_realtime_alert(
                org_id=org_id,
                category=AlertCategory.SECURITY,
                severity=AlertSeverity.CRITICAL,
                event_type="dedupe.test",
                title="Deduped notification",
                source_type="dedupe_test",
                source_id="same-source",
            )
            await db.commit()
            assert alert is not None
            return alert.id

    ids = await asyncio.gather(_create(), _create())
    assert ids[0] == ids[1]

    async with session_factory() as db:
        count = (
            await db.execute(
                select(func.count())
                .select_from(AlertRecord)
                .where(
                    AlertRecord.org_id == org_id,
                    AlertRecord.source_type == "dedupe_test",
                    AlertRecord.source_id == "same-source",
                    AlertRecord.category == AlertCategory.SECURITY,
                )
            )
        ).scalar_one()
        assert count == 1

