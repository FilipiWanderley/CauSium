import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_sync_endpoint_is_idempotent_with_same_key(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-idemp-sync",
            "display_name": "Idemp Sync Sub",
            "tenant_id": "tenant-idemp-sync",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    key = f"sync-key-{uuid4().hex}"
    headers = auth_headers | {"Idempotency-Key": key}

    first = await client.post(f"/api/v1/cloud-accounts/{account_id}/sync", headers=headers)
    assert first.status_code == 200, first.text

    second = await client.post(f"/api/v1/cloud-accounts/{account_id}/sync", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json() == first.json()


@pytest.mark.asyncio
async def test_create_experiment_is_idempotent_with_same_key(client, auth_headers):
    payload = {
        "title": "Idempotent experiment",
        "target_environment": "production",
        "target_criticality": "high",
        "guardrails": {
            "max_blast_radius_pct": 0.2,
            "rollback_on_error_rate": 0.02,
            "max_cost_increase_pct": 0.1,
            "require_approval": True,
        },
    }

    headers = auth_headers | {"Idempotency-Key": f"exp-create-key-{uuid4().hex}"}

    first = await client.post("/api/v1/experiments", json=payload, headers=headers)
    assert first.status_code == 201, first.text

    second = await client.post("/api/v1/experiments", json=payload, headers=headers)
    assert second.status_code == 201, second.text
    assert second.json() == first.json()


@pytest.mark.asyncio
async def test_idempotency_key_conflicts_when_payload_changes(client, auth_headers):
    key = f"exp-create-key-{uuid4().hex}"
    headers = auth_headers | {"Idempotency-Key": key}

    first_payload = {
        "title": "Conflict base payload",
        "target_environment": "production",
        "target_criticality": "medium",
        "guardrails": {
            "max_blast_radius_pct": 0.1,
            "rollback_on_error_rate": 0.02,
            "max_cost_increase_pct": 0.05,
            "require_approval": False,
        },
    }
    second_payload = {
        **first_payload,
        "title": "Conflict changed payload",
    }

    first = await client.post("/api/v1/experiments", json=first_payload, headers=headers)
    assert first.status_code == 201, first.text

    second = await client.post("/api/v1/experiments", json=second_payload, headers=headers)
    assert second.status_code == 409, second.text
