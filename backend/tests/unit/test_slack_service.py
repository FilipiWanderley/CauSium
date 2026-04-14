import pytest
from uuid import UUID

from app.core.security import encrypt_secret
from app.core.slack import SlackService
from app.domains.notifications.models import NotificationSlackConfig


@pytest.mark.asyncio
async def test_send_critical_alert_posts_to_configured_webhook(monkeypatch):
    called = {}

    class _Resp:
        status_code = 200
        text = "ok"

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            called["url"] = url
            called["json"] = json
            return _Resp()

    monkeypatch.setattr("app.core.slack.httpx.AsyncClient", lambda timeout: _Client())

    cfg = NotificationSlackConfig(
        org_id=UUID("00000000-0000-0000-0000-000000000001"),
        enabled=True,
        webhook_encrypted=encrypt_secret("https://hooks.slack.com/services/T0/B0/C0"),
    )

    class _FakeResult:
        def scalar_one_or_none(self):
            return cfg

    class _FakeDB:
        async def execute(self, stmt):
            return _FakeResult()

    service = SlackService(_FakeDB())
    ok = await service.send_critical_alert(
        org_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject="[CauSium][Critical] Test",
        text_body="boom",
    )

    assert ok is True
    assert called["url"].startswith("https://hooks.slack.com/")
    assert "CauSium Critical Alert" in called["json"]["text"]
