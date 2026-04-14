import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_forgot_password_returns_token_when_smtp_disabled(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Forgot Dev Org",
            "org_slug": "forgot-dev-org",
            "email": "forgot-dev@example.com",
            "full_name": "Forgot Dev",
            "password": "securepassword123",
        },
    )
    assert register.status_code == 201, register.text

    resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "forgot-dev@example.com"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data.get("token"), str)
    assert len(data["token"]) >= 20


@pytest.mark.asyncio
async def test_forgot_password_hides_token_when_smtp_enabled(client, monkeypatch):
    monkeypatch.setenv("SMTP_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    get_settings.cache_clear()

    sent = {}

    async def _fake_send_email(self, *, to_email: str, subject: str, text_body: str, html_body: str | None = None):
        sent["to_email"] = to_email
        sent["subject"] = subject
        sent["text_body"] = text_body
        return True

    monkeypatch.setattr("app.core.email.EmailService.send_email", _fake_send_email)

    try:
        register = await client.post(
            "/api/v1/auth/register",
            json={
                "org_name": "Forgot SMTP Org",
                "org_slug": "forgot-smtp-org",
                "email": "forgot-smtp@example.com",
                "full_name": "Forgot SMTP",
                "password": "securepassword123",
            },
        )
        assert register.status_code == 201, register.text

        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot-smtp@example.com"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("token") is None
        assert sent.get("to_email") == "forgot-smtp@example.com"
        assert "Password reset" in sent.get("subject", "")
    finally:
        get_settings.cache_clear()
