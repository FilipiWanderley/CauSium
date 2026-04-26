from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domains.admin.models import DlqStatus, SupportAccessStatus
from app.domains.auth.models import UserRole, WorkspaceLifecycleState


class AdminOrgListItem(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    lifecycle_state: WorkspaceLifecycleState
    member_quota: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserItem(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class AdminForceLifecycle(BaseModel):
    reason: str


class DlqMessageOut(BaseModel):
    id: UUID
    queue_name: str
    org_id: UUID | None
    account_id: UUID | None
    original_payload: str
    error_message: str
    retry_count: int
    status: DlqStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DlqRequeueResponse(BaseModel):
    dlq_id: UUID
    queue_name: str
    requeued: bool


class SloTargetsOut(BaseModel):
    api_error_budget_pct: float
    api_p95_latency_ms: float


class SloGlobalOut(BaseModel):
    requests_total: int
    errors_5xx_total: int
    api_error_rate_pct: float
    api_success_rate_pct: float
    error_budget_burn_rate: float


class SloApiPathOut(BaseModel):
    path: str
    requests: int
    errors_5xx: int
    error_rate_pct: float
    avg_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float


class SloWorkerOut(BaseModel):
    worker: str
    success: int
    retry: int
    failed: int
    locked: int
    total: int
    error_rate_pct: float


class SloWorkerLifecycleOut(BaseModel):
    worker: str
    event: str
    count: int


class SloAlertOut(BaseModel):
    scope: str
    severity: str
    title: str
    detail: str
    recommended_action: str


class SloOverviewOut(BaseModel):
    targets: SloTargetsOut
    global_sli: SloGlobalOut
    api_paths: list[SloApiPathOut]
    workers: list[SloWorkerOut]
    worker_lifecycle: list[SloWorkerLifecycleOut]
    alerts: list[SloAlertOut]


class SupportAccessCreateIn(BaseModel):
    target_org_id: UUID
    reason: str
    duration_minutes: int = 60


class SupportAccessEndIn(BaseModel):
    reason: str


class SupportAccessSessionOut(BaseModel):
    id: UUID
    actor_user_id: UUID
    target_org_id: UUID
    reason: str
    status: SupportAccessStatus
    expires_at: datetime
    created_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}
