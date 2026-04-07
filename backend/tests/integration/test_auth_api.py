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
    assert resp.json()["email"] == "test@example.com"


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
