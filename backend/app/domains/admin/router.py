from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_platform_admin
from app.core.observability import build_sli_slo_snapshot
from app.core.schemas import Page, PageParams
from app.domains.admin.schemas import (
    AdminForceLifecycle,
    AdminOrgListItem,
    AdminUserItem,
    DlqMessageOut,
    DlqRequeueResponse,
    SeedPlatformAdminIn,
    SeedPlatformAdminOut,
    SupportAccessCreateIn,
    SupportAccessEndIn,
    SupportAccessSessionOut,
    SloOverviewOut,
)
from app.domains.auth.models import WorkspaceLifecycleState
from app.domains.admin.service import PlatformAdminService
from app.domains.dev.schemas import SeedRequest, SeedResult, SeedStatus, ClearResult
from app.domains.workspaces.schemas import WorkspaceOut

router = APIRouter(prefix="/admin", tags=["platform-admin"])


@router.post("/seed-platform-admin", response_model=SeedPlatformAdminOut, status_code=200, include_in_schema=False)
async def seed_platform_admin(
    req: SeedPlatformAdminIn,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SeedPlatformAdminOut:
    """Promote an email to PLATFORM_ADMIN. Protected by X-Internal-Key."""
    import os
    from fastapi import HTTPException
    expected = os.getenv("INTERNAL_MONITORING_KEY", "").strip()
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = PlatformAdminService(db, actor_user_id=None)  # type: ignore[arg-type]
    created, promoted = await service.seed_platform_admin(req.email, req.full_name, req.password)
    await db.commit()
    return SeedPlatformAdminOut(email=req.email, created=created, promoted=promoted)


@router.get("/orgs", response_model=Page[AdminOrgListItem])
async def list_all_orgs(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    lifecycle_state: WorkspaceLifecycleState | None = Query(default=None),
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[AdminOrgListItem]:
    """List every organization on the platform (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_orgs(params, q=q, lifecycle_state=lifecycle_state)
    return Page.of(items, total, params)


@router.get("/orgs/{org_id}", response_model=WorkspaceOut)
async def get_org_detail(
    org_id: UUID,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Get full details of any organization (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.get_org(org_id)
    return WorkspaceOut.model_validate(org)


@router.get("/orgs/{org_id}/users", response_model=Page[AdminUserItem])
async def list_org_users(
    org_id: UUID,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[AdminUserItem]:
    """List users of any organization (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_org_users(org_id, params)
    return Page.of(items, total, params)


@router.post("/orgs/{org_id}/suspend", response_model=WorkspaceOut)
async def force_suspend_org(
    org_id: UUID,
    req: AdminForceLifecycle,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Force-suspend any workspace (PLATFORM_ADMIN only). Audited."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.force_suspend(org_id, req.reason)
    await db.commit()
    return WorkspaceOut.model_validate(org)


@router.post("/orgs/{org_id}/restore", response_model=WorkspaceOut)
async def force_restore_org(
    org_id: UUID,
    req: AdminForceLifecycle,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Force-restore a suspended workspace (PLATFORM_ADMIN only). Audited."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.force_restore(org_id, req.reason)
    await db.commit()
    return WorkspaceOut.model_validate(org)


@router.post("/orgs/{org_id}/archive", response_model=WorkspaceOut)
async def force_archive_org(
    org_id: UUID,
    req: AdminForceLifecycle,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Permanently archive any workspace (PLATFORM_ADMIN only). Audited. Irreversible."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.force_archive(org_id, req.reason)
    await db.commit()
    return WorkspaceOut.model_validate(org)


@router.get("/dlq", response_model=Page[DlqMessageOut])
async def list_dlq_messages(
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[DlqMessageOut]:
    """List DLQ messages to support operational triage and UI dashboards."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_dlq(params)
    return Page.of(items, total, params)


@router.post("/dlq/{dlq_id}/requeue", response_model=DlqRequeueResponse)
async def requeue_dlq_message(
    dlq_id: UUID,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> DlqRequeueResponse:
    """Requeue a DLQ message back to its original queue for reprocessing."""
    service = PlatformAdminService(db, current_user.id)
    msg = await service.requeue_dlq(dlq_id)
    await db.commit()
    return DlqRequeueResponse(dlq_id=msg.id, queue_name=msg.queue_name, requeued=True)


@router.get("/observability/slo", response_model=SloOverviewOut)
async def get_slo_overview(
    current_user=Depends(require_platform_admin),
) -> SloOverviewOut:
    _ = current_user
    snapshot = build_sli_slo_snapshot(error_budget_pct=1.0, api_p95_ms_target=500.0)
    return SloOverviewOut(**snapshot)


@router.post("/support-access", response_model=SupportAccessSessionOut, status_code=201)
async def create_support_access(
    req: SupportAccessCreateIn,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SupportAccessSessionOut:
    service = PlatformAdminService(db, current_user.id)
    session = await service.create_support_access_session(
        target_org_id=req.target_org_id,
        reason=req.reason,
        duration_minutes=req.duration_minutes,
    )
    await db.commit()
    return SupportAccessSessionOut.model_validate(session)


@router.get("/support-access/active", response_model=list[SupportAccessSessionOut])
async def list_active_support_access(
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> list[SupportAccessSessionOut]:
    service = PlatformAdminService(db, current_user.id)
    sessions = await service.list_active_support_access_sessions()
    await db.commit()
    return [SupportAccessSessionOut.model_validate(item) for item in sessions]


@router.post("/support-access/{session_id}/end", response_model=SupportAccessSessionOut)
async def end_support_access(
    session_id: UUID,
    req: SupportAccessEndIn,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SupportAccessSessionOut:
    service = PlatformAdminService(db, current_user.id)
    session = await service.end_support_access_session(session_id, reason=req.reason)
    await db.commit()
    return SupportAccessSessionOut.model_validate(session)


def _check_internal_key(x_internal_key: str | None) -> None:
    import os
    from fastapi import HTTPException
    expected = os.getenv("INTERNAL_MONITORING_KEY", "").strip()
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get(
    "/seed-status",
    response_model=SeedStatus,
    include_in_schema=False,
    summary="Check ClickHouse row counts for a tenant",
)
async def admin_seed_status(
    org_id: UUID,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SeedStatus:
    _check_internal_key(x_internal_key)
    from app.domains.dev.service import DevSeedService
    return await DevSeedService(db).status(org_id)


@router.post(
    "/seed-tenant",
    response_model=SeedResult,
    status_code=201,
    include_in_schema=False,
    summary="Seed mock data for a tenant (works in production)",
)
async def admin_seed_tenant(
    org_id: UUID,
    req: SeedRequest,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SeedResult:
    _check_internal_key(x_internal_key)
    from app.domains.dev.service import DevSeedService
    from fastapi import HTTPException
    import traceback
    try:
        return await DevSeedService(db).seed(org_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=traceback.format_exc()) from exc


@router.get(
    "/tenant-audit",
    include_in_schema=False,
    summary="Audit tenant data visibility for a given user email",
)
async def admin_tenant_audit(
    email: str = Query(min_length=5, max_length=255),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)
    from datetime import datetime, timezone

    from fastapi.responses import JSONResponse
    from sqlalchemy import select

    from app.core.clickhouse import execute_query
    from app.domains.auth.models import Organization, User
    from app.domains.cloud_accounts.models import CloudAccount

    normalized_email = email.lower().strip()

    user_result = await db.execute(select(User).where(User.email == normalized_email))
    user = user_result.scalar_one_or_none()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "User not found", "email": normalized_email})

    org = None
    if user.org_id is not None:
        org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
        org = org_result.scalar_one_or_none()

    account_rows: list[CloudAccount] = []
    if user.org_id is not None:
        accounts_result = await db.execute(select(CloudAccount).where(CloudAccount.org_id == user.org_id))
        account_rows = list(accounts_result.scalars().all())

    org_id_str = str(user.org_id) if user.org_id else None

    def _ch_count(table: str, *, org_id: str, account_id: str | None = None) -> int:
        try:
            if account_id:
                rows = execute_query(
                    f"SELECT count() AS cnt FROM {table} WHERE org_id = {{org_id:String}} AND account_id = {{account_id:String}}",
                    {"org_id": org_id, "account_id": account_id},
                )
            else:
                rows = execute_query(
                    f"SELECT count() AS cnt FROM {table} WHERE org_id = {{org_id:String}}",
                    {"org_id": org_id},
                )
            return int(rows[0]["cnt"]) if rows else 0
        except Exception:
            return -1

    def _ch_max_date(table: str, *, org_id: str, account_id: str | None = None, date_col: str = "date") -> str | None:
        try:
            if account_id:
                rows = execute_query(
                    f"SELECT max({date_col}) AS mx FROM {table} WHERE org_id = {{org_id:String}} AND account_id = {{account_id:String}}",
                    {"org_id": org_id, "account_id": account_id},
                )
            else:
                rows = execute_query(
                    f"SELECT max({date_col}) AS mx FROM {table} WHERE org_id = {{org_id:String}}",
                    {"org_id": org_id},
                )
            if not rows:
                return None
            mx = rows[0].get("mx")
            return str(mx) if mx is not None else None
        except Exception:
            return None

    clickhouse = None
    if org_id_str:
        clickhouse = {
            "org": {
                "cost_facts": {"count": _ch_count("cost_facts", org_id=org_id_str), "max_date": _ch_max_date("cost_facts", org_id=org_id_str)},
                "event_facts": {"count": _ch_count("event_facts", org_id=org_id_str), "max_timestamp": _ch_max_date("event_facts", org_id=org_id_str, date_col="timestamp")},
                "usage_facts": {"count": _ch_count("usage_facts", org_id=org_id_str), "max_date": _ch_max_date("usage_facts", org_id=org_id_str)},
                "recommendation_facts": {"count": _ch_count("recommendation_facts", org_id=org_id_str), "max_date": _ch_max_date("recommendation_facts", org_id=org_id_str)},
                "resource_inventory": {"count": _ch_count("resource_inventory", org_id=org_id_str), "max_fetched_at": _ch_max_date("resource_inventory", org_id=org_id_str, date_col="fetched_at")},
            },
            "accounts": [],
        }

        for acc in account_rows:
            acc_id_str = str(acc.id)
            clickhouse["accounts"].append(
                {
                    "account_id": acc_id_str,
                    "provider": acc.provider.value if hasattr(acc.provider, "value") else str(acc.provider),
                    "external_id": acc.external_id,
                    "cost_facts": {"count": _ch_count("cost_facts", org_id=org_id_str, account_id=acc_id_str), "max_date": _ch_max_date("cost_facts", org_id=org_id_str, account_id=acc_id_str)},
                    "event_facts": {"count": _ch_count("event_facts", org_id=org_id_str, account_id=acc_id_str), "max_timestamp": _ch_max_date("event_facts", org_id=org_id_str, account_id=acc_id_str, date_col="timestamp")},
                    "usage_facts": {"count": _ch_count("usage_facts", org_id=org_id_str, account_id=acc_id_str), "max_date": _ch_max_date("usage_facts", org_id=org_id_str, account_id=acc_id_str)},
                    "recommendation_facts": {"count": _ch_count("recommendation_facts", org_id=org_id_str, account_id=acc_id_str), "max_date": _ch_max_date("recommendation_facts", org_id=org_id_str, account_id=acc_id_str)},
                    "resource_inventory": {"count": _ch_count("resource_inventory", org_id=org_id_str, account_id=acc_id_str), "max_fetched_at": _ch_max_date("resource_inventory", org_id=org_id_str, account_id=acc_id_str, date_col="fetched_at")},
                }
            )

    response = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_active": bool(user.is_active),
            "org_id": org_id_str,
        },
        "workspace": (
            {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "plan": org.plan,
                "is_active": bool(org.is_active),
                "lifecycle_state": org.lifecycle_state.value if hasattr(org.lifecycle_state, "value") else str(org.lifecycle_state),
            }
            if org
            else None
        ),
        "cloud_accounts": [
            {
                "id": str(a.id),
                "provider": a.provider.value if hasattr(a.provider, "value") else str(a.provider),
                "external_id": a.external_id,
                "display_name": a.display_name,
                "tenant_id": a.tenant_id,
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
                "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
            }
            for a in account_rows
        ],
        "clickhouse": clickhouse,
    }
    return JSONResponse(response)


@router.get(
    "/seed-diag",
    include_in_schema=False,
    summary="Diagnose seed failure step by step",
)
async def admin_seed_diag(
    org_id: UUID,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)
    import traceback
    import random
    from datetime import date
    from app.domains.dev.service import DevSeedService
    from fastapi.responses import JSONResponse

    steps = {}
    svc = DevSeedService(db)

    try:
        steps["is_seeded"] = await svc.is_seeded(org_id)
    except Exception:
        return JSONResponse({"step": "is_seeded", "error": traceback.format_exc()})

    try:
        accounts = await svc._create_mock_accounts(org_id)
        await db.flush()
        steps["accounts_created"] = len(accounts)
    except Exception:
        return JSONResponse({"step": "_create_mock_accounts", "error": traceback.format_exc()})

    try:
        rng = random.Random(int.from_bytes(org_id.bytes, "big"))
        azure_acct, aws_acct, gcp_acct = accounts
        today = date.today()
        cost_rows = svc._gen_cost_facts(org_id, azure_acct, aws_acct, gcp_acct, today, 30, rng)
        steps["cost_rows"] = len(cost_rows)
    except Exception:
        return JSONResponse({"step": "_gen_cost_facts", "error": traceback.format_exc()})

    try:
        svc._insert_table("cost_facts", cost_rows[:5])
        steps["cost_insert_5_rows"] = "ok"
    except Exception:
        return JSONResponse({"step": "_insert_table cost_facts", "error": traceback.format_exc()})

    try:
        rng2 = random.Random(int.from_bytes(org_id.bytes, "big"))
        change_events = await svc._create_change_events(org_id, accounts, rng2)
        await db.flush()
        steps["change_events_created"] = len(change_events)
    except Exception:
        return JSONResponse({"step": "_create_change_events", "error": traceback.format_exc()})

    # Rollback the test accounts
    await db.rollback()
    return JSONResponse({"steps": steps, "conclusion": "all steps passed"})


@router.delete(
    "/seed-tenant",
    response_model=ClearResult,
    include_in_schema=False,
    summary="Clear seeded mock data for a tenant",
)
async def admin_clear_seed(
    org_id: UUID,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> ClearResult:
    _check_internal_key(x_internal_key)
    from app.domains.dev.service import DevSeedService
    return await DevSeedService(db).clear(org_id)


@router.get(
    "/subscription-audit",
    include_in_schema=False,
    summary="Audit which subscriptions appear in ClickHouse for a cloud account",
)
async def admin_subscription_audit(
    account_id: UUID,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)

    from datetime import datetime, timezone
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from sqlalchemy import desc, select

    from app.core.clickhouse import execute_query
    from app.domains.cloud_accounts.models import CloudAccount, ConnectorHealth

    result = await db.execute(select(CloudAccount).where(CloudAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")

    account_id_str = str(account_id)
    org_id_str = str(account.org_id)

    def _run(query: str, params: dict | None = None):
        try:
            return execute_query(query, params or {})
        except Exception as exc:
            return [{"error": str(exc)}]

    # DISTINCT subscription_ids
    distinct_rows = _run(
        "SELECT DISTINCT subscription_id FROM cost_facts"
        " WHERE org_id = {org_id:String} AND account_id = {account_id:String}"
        " ORDER BY subscription_id",
        {"org_id": org_id_str, "account_id": account_id_str},
    )
    distinct_subscription_ids = [r.get("subscription_id") for r in distinct_rows if "subscription_id" in r]

    table_summaries: dict[str, dict] = {}
    for table, max_col in [("cost_facts", "date"), ("usage_facts", "date"), ("event_facts", "timestamp")]:
        total_rows = _run(
            f"SELECT count() AS row_count, max({max_col}) AS max_value"
            f" FROM {table}"
            " WHERE org_id = {org_id:String} AND account_id = {account_id:String}",
            {"org_id": org_id_str, "account_id": account_id_str},
        )
        distinct_subs = _run(
            f"SELECT DISTINCT subscription_id FROM {table}"
            " WHERE org_id = {org_id:String} AND account_id = {account_id:String}"
            " ORDER BY subscription_id",
            {"org_id": org_id_str, "account_id": account_id_str},
        )
        raw_max = (total_rows[0].get("max_value") if total_rows and isinstance(total_rows[0], dict) else None)
        table_summaries[table] = {
            "row_count": (total_rows[0].get("row_count") if total_rows and isinstance(total_rows[0], dict) else None),
            "max_value": str(raw_max) if raw_max is not None else None,
            "distinct_subscription_ids": [r.get("subscription_id") for r in distinct_subs if "subscription_id" in r],
        }

    # Aggregates per subscription_id
    agg_rows = _run(
        "SELECT subscription_id,"
        " count() AS row_count,"
        " max(date) AS max_date,"
        " round(sum(cost_usd), 4) AS total_cost_usd"
        " FROM cost_facts"
        " WHERE org_id = {org_id:String} AND account_id = {account_id:String}"
        " GROUP BY subscription_id"
        " ORDER BY total_cost_usd DESC",
        {"org_id": org_id_str, "account_id": account_id_str},
    )

    # 5 sample rows per subscription_id
    samples: dict[str, list] = {}
    for sub_id in distinct_subscription_ids:
        if sub_id is None:
            continue
        rows = _run(
            "SELECT subscription_id, service, resource_id, cost_usd, currency, date"
            " FROM cost_facts"
            " WHERE org_id = {org_id:String}"
            "   AND account_id = {account_id:String}"
            "   AND subscription_id = {sub_id:String}"
            " ORDER BY date DESC"
            " LIMIT 5",
            {"org_id": org_id_str, "account_id": account_id_str, "sub_id": sub_id},
        )
        samples[sub_id] = rows

    health_row = await db.execute(
        select(ConnectorHealth)
        .where(ConnectorHealth.account_id == account_id)
        .order_by(desc(ConnectorHealth.checked_at))
        .limit(1)
    )
    last_health = health_row.scalar_one_or_none()

    import json
    from datetime import date as _date, datetime as _datetime

    def _default(obj):
        if isinstance(obj, (_date, _datetime)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id_str,
        "org_id": org_id_str,
        "display_name": account.display_name,
        "external_id": account.external_id,
        "cloud_account_status": str(account.status),
        "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        "connector_health": (
            {
                "checked_at": last_health.checked_at.isoformat() if last_health.checked_at else None,
                "status": str(last_health.status),
                "latency_ms": last_health.latency_ms,
                "message": last_health.message,
            }
            if last_health
            else None
        ),
        "distinct_subscription_ids": distinct_subscription_ids,
        "subscription_count": len(distinct_subscription_ids),
        "table_summaries": table_summaries,
        "aggregates_by_subscription": agg_rows,
        "samples_by_subscription": samples,
    }
    return JSONResponse(content=json.loads(json.dumps(payload, default=_default)))


@router.get(
    "/sync-diag",
    include_in_schema=False,
    summary="Diagnose sync pipeline for a specific account (fast, no network calls)",
)
async def admin_sync_diag(
    org_id: UUID,
    account_id: UUID,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)
    import traceback
    from fastapi.responses import JSONResponse
    from app.domains.cloud_accounts.service import CloudAccountService

    steps: dict = {}

    # Step 1: get account
    try:
        svc = CloudAccountService(db)
        account = await svc.get_account(org_id, account_id)
        if not account:
            return JSONResponse({"step": "get_account", "error": "Account not found"})
        steps["account"] = {
            "status": str(account.status),
            "provider": str(account.provider),
            "external_id": account.external_id,
            "has_credentials_encrypted": bool(getattr(account, "credentials_encrypted", None)),
        }
    except Exception:
        return JSONResponse({"step": "get_account", "error": traceback.format_exc()})

    # Step 2: decrypt credentials
    try:
        creds = await svc.get_azure_credentials(account)
        if creds:
            steps["credentials"] = {
                "found": True,
                "tenant_id": creds.tenant_id,
                "client_id": creds.client_id,
                "subscription_id": creds.subscription_id,
                "storage_account_url": creds.storage_account_url,
                "cost_export_container": creds.cost_export_container,
                "cost_export_prefix": creds.cost_export_prefix,
            }
        else:
            steps["credentials"] = {"found": False}
    except Exception:
        return JSONResponse({"step": "get_credentials", "error": traceback.format_exc()})

    # Step 3: build connector (no network)
    try:
        from app.domains.connectors.factory import get_connector_for_account
        client = get_connector_for_account(account, creds)
        steps["connector"] = type(client).__name__
    except Exception:
        return JSONResponse({"step": "get_connector", "error": traceback.format_exc()})

    return JSONResponse({"steps": steps, "conclusion": "credentials ok — ready to sync"})


@router.post(
    "/force-sync",
    include_in_schema=False,
    summary="Force synchronous ingest for a specific account (bypasses background task)",
)
async def admin_force_sync(
    org_id: UUID,
    account_id: UUID,
    days: int = Query(default=30, ge=7, le=90),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)
    import traceback
    from datetime import date, timedelta
    from fastapi.responses import JSONResponse
    from app.domains.cloud_ledger.service import CloudLedgerService
    from app.domains.decision_engine.service import DecisionEngineService

    end = date.today()
    start = end - timedelta(days=days)

    try:
        ledger = CloudLedgerService(db)
        result = await ledger.ingest_account(org_id, account_id, start, end)
        await db.commit()
    except Exception:
        return JSONResponse({"status": "error", "step": "ingest", "error": traceback.format_exc()}, status_code=500)

    opportunities_generated = 0
    try:
        engine = DecisionEngineService(db)
        opps = await engine.generate_opportunities_for_account(org_id, account_id)
        opportunities_generated = len(opps)
        await db.commit()
    except Exception:
        pass  # non-fatal

    return JSONResponse({
        "status": result.status,
        "message": result.message,
        "cost_records": result.cost_records,
        "event_records": result.event_records,
        "inventory_records": getattr(result, "inventory_records", 0),
        "opportunities_generated": opportunities_generated,
        "days": days,
    })


@router.get(
    "/orgs/{org_id}/subscriptions/discover",
    include_in_schema=False,
    summary="Preview subscriptions found in cost_facts for an org (read-only)",
)
async def admin_discover_subscriptions(
    org_id: UUID,
    account_id: UUID | None = Query(default=None),
    provider: str | None = Query(default=None),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)
    from fastapi.responses import JSONResponse
    from app.domains.cloud_accounts.service import CloudAccountService
    from app.domains.cloud_accounts.schemas import SubscriptionDiscoverOut, DiscoveredSubscriptionRow

    svc = CloudAccountService(db)

    # Validate org exists
    from sqlalchemy import select
    from app.domains.auth.models import Organization
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    if org_result.scalar_one_or_none() is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Organization not found")

    discovery = await svc.discover_subscriptions_from_cost_facts(
        org_id, account_id=account_id, provider=provider
    )
    rows = discovery["subscriptions"]
    skipped_rows = discovery["skipped_subscriptions"]

    # Check which are already registered
    existing_subs, _ = await svc.list_subscriptions(org_id, account_id=account_id)
    registered_keys = {
        (str(s.cloud_account_id), s.provider.value, s.subscription_id)
        for s in existing_subs
    }

    out_rows = []
    already_count = 0
    for r in rows:
        key = (r["cloud_account_id"], r["provider"], r["subscription_id"])
        already = key in registered_keys
        if already:
            already_count += 1
        out_rows.append(DiscoveredSubscriptionRow(
            org_id=r["org_id"],
            cloud_account_id=r["cloud_account_id"],
            provider=r["provider"],
            cloud_tenant_id=r["cloud_tenant_id"],
            subscription_id=r["subscription_id"],
            already_registered=already,
            skipped_reason=r.get("skipped_reason"),
        ))

    out_skipped_rows = [
        DiscoveredSubscriptionRow(
            org_id=r["org_id"],
            cloud_account_id=r["cloud_account_id"],
            provider=r["provider"],
            cloud_tenant_id=r["cloud_tenant_id"],
            subscription_id=r["subscription_id"],
            already_registered=False,
            skipped_reason=r.get("skipped_reason"),
        )
        for r in skipped_rows
    ]

    result = SubscriptionDiscoverOut(
        org_id=str(org_id),
        discovered_count=len(out_rows),
        already_registered_count=already_count,
        new_count=len(out_rows) - already_count,
        skipped_count=len(out_skipped_rows),
        subscriptions=out_rows,
        skipped_subscriptions=out_skipped_rows,
    )
    return JSONResponse(result.model_dump())


@router.post(
    "/orgs/{org_id}/subscriptions/backfill",
    include_in_schema=False,
    summary="Backfill cloud_account_subscriptions from cost_facts (idempotent upsert)",
)
async def admin_backfill_subscriptions(
    org_id: UUID,
    dry_run: bool = Query(default=True),
    account_id: UUID | None = Query(default=None),
    provider: str | None = Query(default=None),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
):
    _check_internal_key(x_internal_key)
    from fastapi.responses import JSONResponse
    from app.domains.cloud_accounts.service import CloudAccountService
    from app.domains.cloud_accounts.schemas import SubscriptionBackfillOut, DiscoveredSubscriptionRow

    svc = CloudAccountService(db)

    # Validate org exists
    from sqlalchemy import select
    from app.domains.auth.models import Organization
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    if org_result.scalar_one_or_none() is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Organization not found")

    result = await svc.backfill_subscriptions_from_cost_facts(
        org_id,
        account_id=account_id,
        provider=provider,
        dry_run=dry_run,
    )

    if not dry_run:
        await db.commit()

    out = SubscriptionBackfillOut(
        org_id=result["org_id"],
        dry_run=result["dry_run"],
        discovered_count=result["discovered_count"],
        inserted_count=result["inserted_count"],
        updated_count=result["updated_count"],
        skipped_count=result["skipped_count"],
        subscriptions=[DiscoveredSubscriptionRow(**r) for r in result["subscriptions"]],
        skipped_subscriptions=[
            DiscoveredSubscriptionRow(**r) for r in result["skipped_subscriptions"]
        ],
    )
    return JSONResponse(out.model_dump())
