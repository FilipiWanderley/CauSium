import pytest


async def _create_opportunity(client, headers, payload: dict) -> dict:
    resp = await client.post("/api/v1/opportunities", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_execution_plan(client, headers, opportunity_ids: list[str], mode: str = "manual_review") -> dict:
    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={"opportunity_ids": opportunity_ids, "mode": mode},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _create_handed_off_execution_plan(client, headers, *, savings: float = 640.0) -> dict:
    op = await _create_opportunity(
        client,
        headers,
        {
            "title": "Execution tracking handoff candidate",
            "description": "Used to validate PulseLab execution tracking.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": savings,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, headers, [op["id"]])
    approve_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Aprovado para tracking"},
        headers=headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    handoff_resp = await client.post(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/handoff",
        json={
            "comment": "Handoff para execucao controlada.",
            "target_environment": "production",
            "target_criticality": "medium",
        },
        headers=headers,
    )
    assert handoff_resp.status_code == 200, handoff_resp.text
    return handoff_resp.json()


@pytest.mark.asyncio
async def test_create_execution_plan_requires_review_and_returns_checklist(client, auth_headers):
    first = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Rightsize VM batch workers",
            "description": "Low sustained usage on workers.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 900.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    second = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Lifecycle optimization for backups",
            "description": "Move cold backups to lower storage tier.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 420.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )

    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={
            "opportunity_ids": [first["id"], second["id"]],
            "mode": "manual_review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "review_required"
    assert data["mode"] == "manual_review"
    assert data["total_savings_monthly"] > 0
    assert data["risk_level"] in {"low", "medium", "high"}
    assert len(data["checklist"]) >= 3
    assert any("sem automacao" in step.lower() for step in data["steps"])


@pytest.mark.asyncio
async def test_create_execution_plan_flags_aks_conflict_gate(client, auth_headers):
    op1 = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "AKS nodepool rightsizing np-app",
            "description": "Reduce baseline node count.",
            "category": "aks_nodepool_rightsizing",
            "resource_id": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/c1/agentPools/np-app",
            "estimated_monthly_savings_usd": 510.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    op2 = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "AKS autoscaler recommendation np-app",
            "description": "Tune min/max autoscaler range.",
            "category": "aks_autoscaler_recommendation",
            "resource_id": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/c1/agentPools/np-app",
            "estimated_monthly_savings_usd": 370.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )

    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={
            "opportunity_ids": [op1["id"], op2["id"]],
            "mode": "manual_review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "review_required"
    assert "aks_conflict_same_nodepool" in data["gates_triggered"]
    assert len(data["conflicts"]) == 1


@pytest.mark.asyncio
async def test_create_execution_plan_blocks_non_positive_savings(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Low value recommendation",
            "description": "No actual savings expected.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 0.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={
            "opportunity_ids": [op["id"]],
            "mode": "manual_review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "blocked"
    assert "non_positive_savings" in data["gates_triggered"]


@pytest.mark.asyncio
async def test_create_execution_plan_persists_and_is_queryable(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Persisted execution plan candidate",
            "description": "Recommendation to validate persistence artifact.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 215.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    create_resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={"opportunity_ids": [op["id"]], "mode": "manual_review"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()

    get_resp = await client.get(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()

    assert fetched["execution_plan_id"] == created["execution_plan_id"]
    assert fetched["selected_opportunity_ids"] == [op["id"]]
    assert fetched["status"] == created["status"]
    assert fetched["risk_level"] == created["risk_level"]
    assert fetched["total_savings_monthly"] == created["total_savings_monthly"]


@pytest.mark.asyncio
async def test_create_execution_plan_emits_audit_event(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Audited execution plan candidate",
            "description": "Should register audit chain event on plan creation.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 180.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    create_resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={"opportunity_ids": [op["id"]], "mode": "manual_review"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.created",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]
    assert len(events) >= 1

    matching = [e for e in events if e["entity_id"] == created["execution_plan_id"]]
    assert len(matching) == 1
    payload = matching[0]["payload"]
    assert payload["execution_plan_id"] == created["execution_plan_id"]
    assert payload["selected_opportunity_ids"] == created["selected_opportunity_ids"]
    assert payload["risk_level"] == created["risk_level"]
    assert payload["status"] == created["status"]
    assert payload["total_savings_monthly"] == created["total_savings_monthly"]


@pytest.mark.asyncio
async def test_update_execution_plan_status_review_required_to_approved_ok(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Approve flow plan",
            "description": "Plan should move from review_required to approved.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 200.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "review_required"

    resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Aprovado para janela noturna"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["status"] == "approved"
    assert updated["execution_plan_id"] == created["execution_plan_id"]


@pytest.mark.asyncio
async def test_update_execution_plan_status_review_required_to_rejected_ok(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Reject from review required",
            "description": "Plan should move to rejected.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 320.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "review_required"

    resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "rejected", "comment": "Risco operacional elevado"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["status"] == "rejected"


@pytest.mark.asyncio
async def test_update_execution_plan_status_blocked_to_approved_fails(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Blocked plan cannot be approved",
            "description": "Zero savings keeps plan blocked.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 0.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "blocked"

    resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Tentativa invalida"},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_update_execution_plan_status_blocked_to_rejected_ok(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Blocked to rejected",
            "description": "Blocked plans can be rejected.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 0.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "blocked"

    resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "rejected", "comment": "Bloqueado e rejeitado"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["status"] == "rejected"


@pytest.mark.asyncio
async def test_update_execution_plan_status_approved_to_rejected_fails(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Approved cannot be rejected",
            "description": "Once approved, transition to rejected is invalid.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 450.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])

    approve_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Primeira aprovacao"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text

    reject_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "rejected", "comment": "Tentativa invalida apos aprovado"},
        headers=auth_headers,
    )
    assert reject_resp.status_code == 422, reject_resp.text


@pytest.mark.asyncio
async def test_update_execution_plan_status_emits_audit_event_with_expected_payload(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Audit payload status update",
            "description": "Approval should generate governance audit payload.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 1230.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])

    comment = "Aprovado para execucao assistida na janela noturna."
    update_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": comment},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["status"] == "approved"

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.approved",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]

    matching = [e for e in events if e["entity_id"] == created["execution_plan_id"]]
    assert len(matching) == 1
    event = matching[0]
    payload = event["payload"]
    assert payload["execution_plan_id"] == created["execution_plan_id"]
    assert payload["previous_status"] == "review_required"
    assert payload["new_status"] == "approved"
    assert payload["actor_user_id"] == event["actor_user_id"]
    assert payload["comment"] == comment
    assert payload["total_savings_monthly"] == created["total_savings_monthly"]
    assert payload["risk_level"] == created["risk_level"]
    assert payload["gates_triggered"] == created["gates_triggered"]


@pytest.mark.asyncio
async def test_schedule_execution_plan_approved_to_scheduled_ok(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Approved plan can be scheduled",
            "description": "Scheduling should be enabled only after approval.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 780.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])

    approve_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Aprovado para agendamento"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text

    schedule_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/schedule",
        json={
            "scheduled_for": "2026-05-12T02:00:00Z",
            "maintenance_window": "janela_noturna_02_04_utc",
            "comment": "Agendado para janela segura.",
        },
        headers=auth_headers,
    )
    assert schedule_resp.status_code == 200, schedule_resp.text
    scheduled = schedule_resp.json()
    assert scheduled["status"] == "scheduled"
    assert scheduled["maintenance_window"] == "janela_noturna_02_04_utc"
    assert scheduled["scheduled_for"] == "2026-05-12T02:00:00+00:00"


@pytest.mark.asyncio
async def test_schedule_execution_plan_requires_approved_status(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Review required cannot be scheduled",
            "description": "Only approved plans can move to scheduled.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 350.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "review_required"

    schedule_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/schedule",
        json={
            "scheduled_for": "2026-05-13T01:00:00Z",
            "maintenance_window": "janela_madrugada",
            "comment": "Tentativa invalida sem aprovacao.",
        },
        headers=auth_headers,
    )
    assert schedule_resp.status_code == 422, schedule_resp.text


@pytest.mark.asyncio
async def test_schedule_execution_plan_emits_audit_event_with_expected_payload(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Schedule audit payload",
            "description": "Scheduling should emit expected audit payload.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 1230.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])

    approve_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Aprovado para scheduling"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text

    comment = "Agendado para janela noturna de manutencao."
    schedule_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/schedule",
        json={
            "scheduled_for": "2026-05-14T03:00:00Z",
            "maintenance_window": "janela_noturna_03_05_utc",
            "comment": comment,
        },
        headers=auth_headers,
    )
    assert schedule_resp.status_code == 200, schedule_resp.text
    scheduled = schedule_resp.json()
    assert scheduled["status"] == "scheduled"

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.scheduled",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]

    matching = [e for e in events if e["entity_id"] == created["execution_plan_id"]]
    assert len(matching) == 1
    payload = matching[0]["payload"]
    assert payload["execution_plan_id"] == created["execution_plan_id"]
    assert payload["previous_status"] == "approved"
    assert payload["new_status"] == "scheduled"
    assert payload["scheduled_for"] == "2026-05-14T03:00:00+00:00"
    assert payload["maintenance_window"] == "janela_noturna_03_05_utc"
    assert payload["comment"] == comment
    assert payload["total_savings_monthly"] == created["total_savings_monthly"]
    assert payload["risk_level"] == created["risk_level"]
    assert payload["gates_triggered"] == created["gates_triggered"]


@pytest.mark.asyncio
async def test_create_execution_plan_handoff_from_scheduled_creates_experiment_and_link(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Scheduled plan can be handed off",
            "description": "Scheduled plans should create PulseLab handoff.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 640.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "review_required"

    approve_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Aprovado para handoff"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text

    schedule_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/schedule",
        json={
            "scheduled_for": "2026-05-20T02:00:00Z",
            "maintenance_window": "janela_noturna_02_04_utc",
            "comment": "Agendado para handoff controlado.",
        },
        headers=auth_headers,
    )
    assert schedule_resp.status_code == 200, schedule_resp.text
    scheduled = schedule_resp.json()
    assert scheduled["status"] == "scheduled"

    handoff_comment = "Enviar para PulseLab sem aplicacao automatica."
    handoff_resp = await client.post(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/handoff",
        json={
            "comment": handoff_comment,
            "target_environment": "production",
            "target_criticality": "high",
        },
        headers=auth_headers,
    )
    assert handoff_resp.status_code == 200, handoff_resp.text
    handed_off = handoff_resp.json()
    assert handed_off["mode"] == "pulselab_handoff"
    assert handed_off["status"] == "scheduled"
    assert handed_off["pulselab_experiment_id"] is not None
    assert len(handed_off["handoff_checklist"]) >= len(scheduled["checklist"])

    experiment_resp = await client.get(
        f"/api/v1/experiments/{handed_off['pulselab_experiment_id']}",
        headers=auth_headers,
    )
    assert experiment_resp.status_code == 200, experiment_resp.text
    experiment = experiment_resp.json()
    assert experiment["title"].startswith("PulseLab handoff for execution plan")
    assert experiment["status"] == "draft"


@pytest.mark.asyncio
async def test_create_execution_plan_handoff_requires_approved_or_scheduled_status(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Review required cannot handoff",
            "description": "Only approved or scheduled should be accepted.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 410.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    assert created["status"] == "review_required"

    handoff_resp = await client.post(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/handoff",
        json={
            "comment": "Tentativa invalida.",
            "target_environment": "production",
            "target_criticality": "medium",
        },
        headers=auth_headers,
    )
    assert handoff_resp.status_code == 422, handoff_resp.text


@pytest.mark.asyncio
async def test_create_execution_plan_handoff_emits_audit_event_with_expected_payload(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Handoff audit payload",
            "description": "Handoff should emit governance audit payload.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 990.0,
            "risk_level": "high",
            "effort_level": "medium",
        },
    )
    created = await _create_execution_plan(client, auth_headers, [op["id"]])
    approve_resp = await client.patch(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/status",
        json={"status": "approved", "comment": "Aprovado para handoff"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text

    comment = "Handoff para experimento controlado no PulseLab."
    handoff_resp = await client.post(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}/handoff",
        json={
            "comment": comment,
            "target_environment": "production",
            "target_criticality": "high",
        },
        headers=auth_headers,
    )
    assert handoff_resp.status_code == 200, handoff_resp.text
    handed_off = handoff_resp.json()
    assert handed_off["pulselab_experiment_id"] is not None

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.handoff_created",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]

    matching = [e for e in events if e["entity_id"] == created["execution_plan_id"]]
    assert len(matching) == 1
    payload = matching[0]["payload"]
    assert payload["execution_plan_id"] == created["execution_plan_id"]
    assert payload["experiment_id"] == handed_off["pulselab_experiment_id"]
    assert payload["new_mode"] == "pulselab_handoff"
    assert payload["status"] == "approved"
    assert payload["target_environment"] == "production"
    assert payload["target_criticality"] == "high"
    assert payload["comment"] == comment
    assert isinstance(payload["final_checklist"], list)
    assert len(payload["final_checklist"]) >= 1
    assert payload["total_savings_monthly"] == created["total_savings_monthly"]
    assert payload["risk_level"] == created["risk_level"]
    assert payload["gates_triggered"] == created["gates_triggered"]


@pytest.mark.asyncio
async def test_get_execution_plan_execution_status_syncs_running_and_emits_started_event(client, auth_headers):
    handed_off = await _create_handed_off_execution_plan(client, auth_headers, savings=210.0)

    status_resp = await client.get(
        f"/api/v1/intel/execution-plan/{handed_off['execution_plan_id']}/execution-status",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200, status_resp.text
    data = status_resp.json()
    assert data["execution_plan_id"] == handed_off["execution_plan_id"]
    assert data["experiment_id"] == handed_off["pulselab_experiment_id"]
    assert data["status"] == "running"
    assert data["outcome"] == "partial"
    assert data["expected_savings"] == 210.0
    assert data["actual_savings"] == 0.0
    assert data["delta"] == -210.0

    plan_resp = await client.get(
        f"/api/v1/intel/execution-plan/{handed_off['execution_plan_id']}",
        headers=auth_headers,
    )
    assert plan_resp.status_code == 200, plan_resp.text
    plan = plan_resp.json()
    assert plan["experiment_status"] == "running"
    assert plan["execution_outcome"] == "partial"
    assert plan["actual_savings"] == 0.0
    assert isinstance(plan["experiment_result"], dict)

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.execution_started",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    matching = [e for e in events_resp.json()["items"] if e["entity_id"] == handed_off["execution_plan_id"]]
    assert len(matching) == 1
    assert matching[0]["payload"]["new_status"] == "running"


@pytest.mark.asyncio
async def test_get_execution_plan_execution_status_tracks_completed_and_failed(client, auth_headers):
    completed_plan = await _create_handed_off_execution_plan(client, auth_headers, savings=210.0)
    completed_experiment_id = completed_plan["pulselab_experiment_id"]
    assert completed_experiment_id is not None

    for next_status in ["hypothesis", "simulating", "approved"]:
        move_resp = await client.post(
            f"/api/v1/experiments/{completed_experiment_id}/transition",
            json={"status": next_status},
            headers=auth_headers,
        )
        assert move_resp.status_code == 200, move_resp.text

    running_resp = await client.post(
        f"/api/v1/experiments/{completed_experiment_id}/transition",
        json={"status": "running"},
        headers=auth_headers
        | {"X-Session-Risk": "low", "X-Maintenance-Window": "true", "X-Device-Trusted": "true"},
    )
    assert running_resp.status_code == 200, running_resp.text
    measuring_resp = await client.post(
        f"/api/v1/experiments/{completed_experiment_id}/transition",
        json={"status": "measuring"},
        headers=auth_headers,
    )
    assert measuring_resp.status_code == 200, measuring_resp.text

    patch_resp = await client.patch(
        f"/api/v1/experiments/{completed_experiment_id}",
        json={"outcome": "improved", "actual_savings_usd": 180.0},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    concluded_resp = await client.post(
        f"/api/v1/experiments/{completed_experiment_id}/transition",
        json={"status": "concluded"},
        headers=auth_headers,
    )
    assert concluded_resp.status_code == 200, concluded_resp.text

    completed_status_resp = await client.get(
        f"/api/v1/intel/execution-plan/{completed_plan['execution_plan_id']}/execution-status",
        headers=auth_headers,
    )
    assert completed_status_resp.status_code == 200, completed_status_resp.text
    completed_data = completed_status_resp.json()
    assert completed_data["status"] == "completed"
    assert completed_data["outcome"] == "success"
    assert completed_data["expected_savings"] == 210.0
    assert completed_data["actual_savings"] == 180.0
    assert completed_data["delta"] == -30.0

    failed_plan = await _create_handed_off_execution_plan(client, auth_headers, savings=120.0)
    failed_experiment_id = failed_plan["pulselab_experiment_id"]
    assert failed_experiment_id is not None
    cancel_resp = await client.post(
        f"/api/v1/experiments/{failed_experiment_id}/transition",
        json={"status": "cancelled"},
        headers=auth_headers,
    )
    assert cancel_resp.status_code == 200, cancel_resp.text

    failed_status_resp = await client.get(
        f"/api/v1/intel/execution-plan/{failed_plan['execution_plan_id']}/execution-status",
        headers=auth_headers,
    )
    assert failed_status_resp.status_code == 200, failed_status_resp.text
    failed_data = failed_status_resp.json()
    assert failed_data["status"] == "failed"
    assert failed_data["outcome"] == "failed"

    completed_events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.execution_completed",
        headers=auth_headers,
    )
    assert completed_events_resp.status_code == 200, completed_events_resp.text
    completed_matching = [
        e for e in completed_events_resp.json()["items"] if e["entity_id"] == completed_plan["execution_plan_id"]
    ]
    assert len(completed_matching) == 1

    failed_events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.execution_failed",
        headers=auth_headers,
    )
    assert failed_events_resp.status_code == 200, failed_events_resp.text
    failed_matching = [e for e in failed_events_resp.json()["items"] if e["entity_id"] == failed_plan["execution_plan_id"]]
    assert len(failed_matching) == 1


@pytest.mark.asyncio
async def test_execution_tracking_calibrates_confidence_up_for_high_accuracy(client, auth_headers):
    plan = await _create_handed_off_execution_plan(client, auth_headers, savings=200.0)
    experiment_id = plan["pulselab_experiment_id"]
    assert experiment_id is not None

    for next_status in ["hypothesis", "simulating", "approved"]:
        move_resp = await client.post(
            f"/api/v1/experiments/{experiment_id}/transition",
            json={"status": next_status},
            headers=auth_headers,
        )
        assert move_resp.status_code == 200, move_resp.text
    running_resp = await client.post(
        f"/api/v1/experiments/{experiment_id}/transition",
        json={"status": "running"},
        headers=auth_headers
        | {"X-Session-Risk": "low", "X-Maintenance-Window": "true", "X-Device-Trusted": "true"},
    )
    assert running_resp.status_code == 200, running_resp.text
    measuring_resp = await client.post(
        f"/api/v1/experiments/{experiment_id}/transition",
        json={"status": "measuring"},
        headers=auth_headers,
    )
    assert measuring_resp.status_code == 200, measuring_resp.text
    patch_resp = await client.patch(
        f"/api/v1/experiments/{experiment_id}",
        json={"outcome": "improved", "actual_savings_usd": 190.0},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    concluded_resp = await client.post(
        f"/api/v1/experiments/{experiment_id}/transition",
        json={"status": "concluded"},
        headers=auth_headers,
    )
    assert concluded_resp.status_code == 200, concluded_resp.text

    sync_resp = await client.get(
        f"/api/v1/intel/execution-plan/{plan['execution_plan_id']}/execution-status",
        headers=auth_headers,
    )
    assert sync_resp.status_code == 200, sync_resp.text

    plan_resp = await client.get(
        "/api/v1/intel/optimization-plan",
        headers=auth_headers,
    )
    assert plan_resp.status_code == 200, plan_resp.text
    prioritized = plan_resp.json()["prioritized"]
    target_id = str(plan["selected_opportunity_ids"][0])
    target = next((item for item in prioritized if str(item["opportunity_id"]) == target_id), None)
    assert target is not None
    assert target["historical_accuracy"] is not None
    assert target["historical_accuracy"] >= 0.8
    assert target["confidence_adjustment"] > 0
    assert target["confidence"] > target["base_confidence"]


@pytest.mark.asyncio
async def test_execution_tracking_calibrates_confidence_down_for_low_accuracy(client, auth_headers):
    plan = await _create_handed_off_execution_plan(client, auth_headers, savings=200.0)
    experiment_id = plan["pulselab_experiment_id"]
    assert experiment_id is not None

    patch_resp = await client.patch(
        f"/api/v1/experiments/{experiment_id}",
        json={"outcome": "regressed", "actual_savings_usd": 40.0},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    cancel_resp = await client.post(
        f"/api/v1/experiments/{experiment_id}/transition",
        json={"status": "cancelled"},
        headers=auth_headers,
    )
    assert cancel_resp.status_code == 200, cancel_resp.text

    sync_resp = await client.get(
        f"/api/v1/intel/execution-plan/{plan['execution_plan_id']}/execution-status",
        headers=auth_headers,
    )
    assert sync_resp.status_code == 200, sync_resp.text

    plan_resp = await client.get(
        "/api/v1/intel/optimization-plan",
        headers=auth_headers,
    )
    assert plan_resp.status_code == 200, plan_resp.text
    prioritized = plan_resp.json()["prioritized"]
    target_id = str(plan["selected_opportunity_ids"][0])
    target = next((item for item in prioritized if str(item["opportunity_id"]) == target_id), None)
    assert target is not None
    assert target["historical_accuracy"] is not None
    assert target["historical_accuracy"] < 0.5
    assert target["confidence_adjustment"] < 0
    assert target["confidence"] < target["base_confidence"]


@pytest.mark.asyncio
async def test_list_execution_plans_with_status_and_risk_filters(client, auth_headers):
    low = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "History list low risk",
            "description": "List endpoint should include this plan.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 240.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    medium = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "History list medium risk",
            "description": "List endpoint should filter by risk level.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 330.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    blocked = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "History list blocked status",
            "description": "Non-positive savings should block.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 0.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    for opp_id in [low["id"], medium["id"], blocked["id"]]:
        resp = await client.post(
            "/api/v1/intel/execution-plan",
            json={"opportunity_ids": [opp_id], "mode": "manual_review"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text

    blocked_resp = await client.get("/api/v1/intel/execution-plan?status=blocked", headers=auth_headers)
    assert blocked_resp.status_code == 200, blocked_resp.text
    blocked_data = blocked_resp.json()
    assert blocked_data["total"] >= 1
    assert all(item["status"] == "blocked" for item in blocked_data["items"])

    medium_resp = await client.get("/api/v1/intel/execution-plan?risk_level=medium", headers=auth_headers)
    assert medium_resp.status_code == 200, medium_resp.text
    medium_data = medium_resp.json()
    assert medium_data["total"] >= 1
    assert all(item["risk_level"] == "medium" for item in medium_data["items"])


@pytest.mark.asyncio
async def test_list_execution_plans_supports_pagination_and_created_to_filter(client, auth_headers):
    for idx in range(2):
        opp = await _create_opportunity(
            client,
            auth_headers,
            {
                "title": f"History pagination {idx}",
                "description": "Create plans for queue pagination.",
                "category": "rightsizing",
                "estimated_monthly_savings_usd": 110.0 + idx,
                "risk_level": "low",
                "effort_level": "low",
            },
        )
        create_resp = await client.post(
            "/api/v1/intel/execution-plan",
            json={"opportunity_ids": [opp["id"]], "mode": "manual_review"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200, create_resp.text

    page1_resp = await client.get("/api/v1/intel/execution-plan?page=1&page_size=1", headers=auth_headers)
    assert page1_resp.status_code == 200, page1_resp.text
    page1 = page1_resp.json()
    assert page1["page"] == 1
    assert page1["page_size"] == 1
    assert page1["total"] >= 2
    assert len(page1["items"]) == 1
    assert page1["has_next"] is True

    page2_resp = await client.get("/api/v1/intel/execution-plan?page=2&page_size=1", headers=auth_headers)
    assert page2_resp.status_code == 200, page2_resp.text
    page2 = page2_resp.json()
    assert page2["page"] == 2
    assert len(page2["items"]) == 1
    assert page2["items"][0]["execution_plan_id"] != page1["items"][0]["execution_plan_id"]

    old_window_resp = await client.get(
        "/api/v1/intel/execution-plan?created_to=2000-01-01T00:00:00Z",
        headers=auth_headers,
    )
    assert old_window_resp.status_code == 200, old_window_resp.text
    old_window = old_window_resp.json()
    assert old_window["total"] == 0
