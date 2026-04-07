import pytest

from app.core.email import EmailService


@pytest.mark.asyncio
async def test_email_service_disabled_returns_false(monkeypatch):
    service = EmailService()

    monkeypatch.setattr(service.settings, "smtp_enabled", False)

    ok = await service.send_email(
        to_email="user@example.com",
        subject="Test",
        text_body="body",
    )

    assert ok is False


@pytest.mark.asyncio
async def test_email_service_enabled_uses_sync_sender(monkeypatch):
    service = EmailService()

    monkeypatch.setattr(service.settings, "smtp_enabled", True)
    monkeypatch.setattr(service.settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(service.settings, "smtp_from_email", "noreply@example.com")

    called = {"sent": False}

    def _fake_send_sync(msg):
        called["sent"] = True
        assert msg["To"] == "user@example.com"
        assert msg["Subject"] == "Test"

    monkeypatch.setattr(service, "_send_sync", _fake_send_sync)

    ok = await service.send_email(
        to_email="user@example.com",
        subject="Test",
        text_body="body",
    )

    assert ok is True
    assert called["sent"] is True


@pytest.mark.asyncio
async def test_critical_alert_without_recipients(monkeypatch):
    service = EmailService()
    monkeypatch.setattr(service.settings, "smtp_alert_to", "")

    sent = await service.send_critical_alert(
        subject="Critical",
        text_body="Failure",
    )

    assert sent == 0
