import pytest
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_create_initiative(client, auth_headers):
    resp = await client.post(
        "/api/v1/initiatives",
        json={
            "title": "Rightsize VM fleet Q1",
            "description": "Execute VM rightsizing playbook",
            "sla_date": (date.today() + timedelta(days=30)).isoformat(),
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    i = resp.json()
    assert i["status"] == "backlog"
    assert i["is_overdue"] is False


@pytest.mark.asyncio
async def test_status_transition(client, auth_headers):
    create = await client.post(
        "/api/v1/initiatives",
        json={"title": "Transition test"},
        headers=auth_headers,
    )
    iid = create.json()["id"]

    # backlog → planned
    r = await client.post(
        f"/api/v1/initiatives/{iid}/transition",
        json={"status": "planned"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "planned"

    # planned → in_progress
    r2 = await client.post(
        f"/api/v1/initiatives/{iid}/transition",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_invalid_transition(client, auth_headers):
    create = await client.post(
        "/api/v1/initiatives",
        json={"title": "Invalid transition test"},
        headers=auth_headers,
    )
    iid = create.json()["id"]

    # backlog → done (invalid)
    r = await client.post(
        f"/api/v1/initiatives/{iid}/transition",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_board(client, auth_headers):
    resp = await client.get("/api/v1/initiatives/board", headers=auth_headers)
    assert resp.status_code == 200
    board = resp.json()
    assert all(k in board for k in ["backlog", "planned", "in_progress", "review", "done", "cancelled"])


@pytest.mark.asyncio
async def test_comments(client, auth_headers):
    create = await client.post(
        "/api/v1/initiatives",
        json={"title": "Comment test initiative"},
        headers=auth_headers,
    )
    iid = create.json()["id"]

    # Add comment
    c = await client.post(
        f"/api/v1/initiatives/{iid}/comments",
        json={"body": "This is a test comment"},
        headers=auth_headers,
    )
    assert c.status_code == 201

    # List
    list_r = await client.get(f"/api/v1/initiatives/{iid}/comments", headers=auth_headers)
    assert list_r.status_code == 200
    assert len(list_r.json()) == 1
    assert list_r.json()[0]["body"] == "This is a test comment"
