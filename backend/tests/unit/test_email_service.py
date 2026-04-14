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


@pytest.mark.asyncio
async def test_critical_alert_uses_product_template(monkeypatch):
    service = EmailService()
    monkeypatch.setattr(service.settings, "smtp_alert_to", "ops@example.com")

    sent_payload = {}

    async def _fake_send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None):
        sent_payload["to_email"] = to_email
        sent_payload["subject"] = subject
        sent_payload["text_body"] = text_body
        sent_payload["html_body"] = html_body
        return True

    monkeypatch.setattr(service, "send_email", _fake_send_email)

    sent = await service.send_critical_alert(
        subject="[CauSium][Critical] Worker failure",
        text_body="error: boom",
    )

    assert sent == 1
    assert sent_payload["to_email"] == "ops@example.com"
    assert "CauSium - Alerta Critico" in sent_payload["text_body"]
    assert "Acoes recomendadas:" in sent_payload["text_body"]
    assert sent_payload["html_body"] is not None
    assert "<ol" in sent_payload["html_body"]
