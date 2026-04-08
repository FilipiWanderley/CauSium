import pytest


@pytest.mark.asyncio
async def test_admin_create_preview_accept_invite_flow(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/invites",
        headers=auth_headers,
        json={
            "email": "invite-flow-user@example.com",
            "role": "viewer",
            "expires_in_days": 7,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    invite = create_resp.json()
    token = invite["token"]

    preview_resp = await client.get(f"/api/v1/invites/{token}/preview")
    assert preview_resp.status_code == 200, preview_resp.text
    preview = preview_resp.json()
    assert preview["invited_email"] == "invite-flow-user@example.com"
    assert preview["status"] == "pending"
    assert preview["role"] == "viewer"

    accept_resp = await client.post(
        f"/api/v1/invites/{token}/accept",
        json={
            "full_name": "Invite Flow User",
            "password": "InviteFlow@123",
        },
    )
    assert accept_resp.status_code == 201, accept_resp.text
    accepted_user = accept_resp.json()
    assert accepted_user["email"] == "invite-flow-user@example.com"
    assert accepted_user["role"] == "viewer"

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "invite-flow-user@example.com",
            "password": "InviteFlow@123",
        },
    )
    assert login_resp.status_code == 200, login_resp.text


@pytest.mark.asyncio
async def test_admin_revoke_invite_prevents_accept(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/invites",
        headers=auth_headers,
        json={
            "email": "invite-revoke-user@example.com",
            "role": "engineer",
            "expires_in_days": 7,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    invite = create_resp.json()

    revoke_resp = await client.delete(
        f"/api/v1/invites/{invite['id']}",
        headers=auth_headers,
    )
    assert revoke_resp.status_code == 204, revoke_resp.text

    accept_resp = await client.post(
        f"/api/v1/invites/{invite['token']}/accept",
        json={
            "full_name": "Revoke User",
            "password": "InviteFlow@123",
        },
    )
    assert accept_resp.status_code == 409, accept_resp.text
    assert "cannot be accepted" in accept_resp.json()["detail"]
