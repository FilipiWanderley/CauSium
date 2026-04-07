import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Acme Corp",
        "org_slug": "acme-corp",
        "email": "admin@acme.com",
        "full_name": "Acme Admin",
        "password": "securepassword123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@acme.com"
    assert data["user"]["role"] == "admin"
    # SP-A01: org founder does not need to change password (already chose it)
    assert data["user"]["must_change_password"] is False
    set_cookie = resp.headers.get("set-cookie", "")
    assert "sp_access_token=" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.asyncio
async def test_register_duplicate_slug(client):
    payload = {
        "org_name": "Dup Org",
        "org_slug": "dup-org",
        "email": "a@dup.com",
        "full_name": "User A",
        "password": "password123",
    }
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    payload["email"] = "b@dup.com"
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/v1/auth/register", json={
        "org_name": "Login Org",
        "org_slug": "login-org",
        "email": "login@test.com",
        "full_name": "Login User",
        "password": "mypassword123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "mypassword123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"].endswith("@example.com")


@pytest.mark.asyncio
async def test_me_no_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_cookie_auth(client):
    register_resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Cookie Org",
        "org_slug": "cookie-org",
        "email": "cookie@test.com",
        "full_name": "Cookie User",
        "password": "cookiepassword123",
    })
    assert register_resp.status_code == 201

    me_resp = await client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "cookie@test.com"


@pytest.mark.asyncio
async def test_logout_clears_cookie_session(client):
    register_resp = await client.post("/api/v1/auth/register", json={
        "org_name": "Logout Org",
        "org_slug": "logout-org",
        "email": "logout@test.com",
        "full_name": "Logout User",
        "password": "logoutpassword123",
    })
    assert register_resp.status_code == 201

    me_before = await client.get("/api/v1/auth/me")
    assert me_before.status_code == 200

    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204

    me_after = await client.get("/api/v1/auth/me")
    assert me_after.status_code == 401


# ---------------------------------------------------------------------------
# SP-A04: Origin / Referer validation
# ---------------------------------------------------------------------------

# In non-production tests, requests without an Origin header are allowed
# (automated test clients don't send browser headers). These tests confirm:
#   - A valid allowed origin is accepted
#   - An unknown origin is rejected with 403
#   - Referer is accepted as fallback
#   - GET requests on the same path are never blocked (not state-mutating)


@pytest.mark.asyncio
async def test_origin_validation_allowed_origin_accepted(client):
    """Requests from a configured allowed origin must pass the origin check."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "irrelevant"},
        headers={"Origin": "http://localhost:5173"},
    )
    # Credentials are wrong, but 401 means origin check passed.
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_origin_validation_unknown_origin_rejected(client):
    """Requests from an unrecognised origin must be rejected with 403."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "irrelevant"},
        headers={"Origin": "https://evil.example.com"},
    )
    assert resp.status_code == 403
    assert "Origin not allowed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_origin_validation_referer_fallback_accepted(client):
    """A valid Referer header must be accepted when Origin is absent."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "irrelevant"},
        headers={"Referer": "http://localhost:5173/login"},
    )
    assert resp.status_code == 401  # origin ok, credentials wrong → 401


@pytest.mark.asyncio
async def test_origin_validation_referer_unknown_rejected(client):
    """An unrecognised Referer origin must be rejected with 403."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "irrelevant"},
        headers={"Referer": "https://evil.example.com/phishing"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_origin_validation_get_not_blocked(client, auth_headers):
    """GET requests are never subject to origin validation."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={**auth_headers, "Origin": "https://evil.example.com"},
    )
    # GET /auth/me is not in the validated paths; unknown origin is irrelevant.
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_origin_validation_no_origin_allowed_in_non_prod(client):
    """In non-production, requests without any Origin/Referer are allowed through."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "wrong"},
        # No Origin / Referer — simulates an API client or test runner.
    )
    # Non-production: check is skipped → auth layer responds with 401.
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SP-A01: Force password change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_created_user_must_change_password(client, auth_headers):
    """Users created by an admin must have must_change_password=True."""
    resp = await client.post(
        "/api/v1/auth/users",
        json={"email": "newmember@test.com", "full_name": "New Member", "password": "temppass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_change_password_success(client, auth_headers):
    """Authenticated user can change their password; flag is cleared."""
    # Set must_change_password=True on the test user via create path is not
    # straightforward — instead verify the endpoint mechanics with the test user
    # (who registered directly, so must_change_password=False but can still call it).
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpassword123", "new_password": "newpassword456"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is False


@pytest.mark.asyncio
async def test_change_password_wrong_current(client, auth_headers):
    """Wrong current password returns 400."""
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong_password", "new_password": "newpassword456"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_same_password_rejected(client, auth_headers):
    """New password must differ from current; same password returns 400."""
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpassword123", "new_password": "testpassword123"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "differ" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_unauthenticated(client):
    """Change-password requires authentication."""
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "any", "new_password": "newpassword456"},
    )
    assert resp.status_code == 401
