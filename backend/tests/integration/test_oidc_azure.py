import pytest

from app.domains.auth.service import AuthService


@pytest.mark.asyncio
async def test_azure_oidc_callback_redirects_with_tokens(client, auth_headers, monkeypatch):
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    user_email = me.json()["email"]

    async def fake_login_with_azure_oidc_callback(self, code: str, state: str):
        user = await self.get_user_by_email(user_email)
        return user, "fake_access_token", "fake_refresh_token"

    monkeypatch.setattr(AuthService, "login_with_azure_oidc_callback", fake_login_with_azure_oidc_callback)
    response = await client.get(
        "/api/v1/auth/oidc/azure/callback?code=demo-code&state=demo-state",
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "access_token=fake_access_token" in location
    assert "refresh_token=fake_refresh_token" in location
