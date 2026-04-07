from uuid import uuid4

import pytest

from app.domains.admin.models import DlqMessage, DlqStatus


@pytest.mark.asyncio
async def test_platform_admin_lists_dlq(client, db, platform_admin_headers):
    msg = DlqMessage(
        queue_name="ingestion:queue",
        org_id=None,
        account_id=None,
        original_payload='{"org_id":"o","account_id":"a"}',
        error_message="boom",
        retry_count=3,
        status=DlqStatus.OPEN,
    )
    db.add(msg)
    await db.flush()

    resp = await client.get("/api/v1/admin/dlq", headers=platform_admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["id"] == str(msg.id) for item in data["items"])


@pytest.mark.asyncio
async def test_platform_admin_requeues_dlq(client, db, platform_admin_headers, monkeypatch):
    msg = DlqMessage(
        queue_name="scoring:queue",
        org_id=None,
        account_id=None,
        original_payload='{"org_id":"x","account_id":"y"}',
        error_message="failed",
        retry_count=3,
        status=DlqStatus.OPEN,
    )
    db.add(msg)
    await db.flush()

    pushed = {"queue": None, "payload": None}

    class _FakeRedis:
        async def lpush(self, queue, payload):
            pushed["queue"] = queue
            pushed["payload"] = payload

    monkeypatch.setattr("app.domains.admin.service.get_redis_pool", lambda: _FakeRedis())

    resp = await client.post(
        f"/api/v1/admin/dlq/{msg.id}/requeue",
        headers=platform_admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["requeued"] is True
    assert pushed["queue"] == "scoring:queue"
    assert pushed["payload"] == '{"org_id":"x","account_id":"y"}'

    await db.refresh(msg)
    assert msg.status == DlqStatus.REQUEUED


@pytest.mark.asyncio
async def test_non_platform_admin_cannot_access_dlq(client, auth_headers):
    resp = await client.get("/api/v1/admin/dlq", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_requeue_missing_dlq_returns_404(client, platform_admin_headers):
    missing = uuid4()
    resp = await client.post(
        f"/api/v1/admin/dlq/{missing}/requeue",
        headers=platform_admin_headers,
    )
    assert resp.status_code == 404
