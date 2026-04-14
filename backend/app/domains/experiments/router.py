from __future__ import annotations
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.policy import authorize_experiment_action
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_session_context
from app.core.idempotency import build_fingerprint, build_scope_key, prepare_request, store_response
from app.core.redis import get_redis_pool
from app.core.schemas import Page, PageParams
from app.domains.experiments.models import ExperimentStatus
from app.domains.experiments.schemas import (
    ExperimentApprovalCreate,
    ExperimentApprovalOut,
    ExperimentCreate,
    ExperimentOut,
    ExperimentSummary,
    ExperimentTransition,
    ExperimentUpdate,
    RunCreate,
    RunOut,
    RunUpdate,
)
from app.domains.policy.service import PolicyService
from app.domains.experiments.service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["experiments"])


async def _evaluate_and_record_policy(
    *,
    db: AsyncSession,
    current_user,
    session,
    response: Response,
    action: str,
    experiment,
    approval_count: int,
    requires_dual_approval: bool,
) -> None:
    decision = authorize_experiment_action(
        action=action,
        role=current_user.role,
        environment=experiment.target_environment,
        criticality=experiment.target_criticality,
        session=session,
        requires_dual_approval=requires_dual_approval,
        approval_count=approval_count,
    )
    policy_service = PolicyService(db)
    await policy_service.record_decision(
        org_id=current_user.org_id,
        actor_user_id=current_user.id,
        decision=decision,
        session=session,
        action=action,
        resource_type="optimization_experiment",
        resource_id=str(experiment.id),
    )
    response.headers["X-Policy-Decision-Id"] = decision.policy_decision_id
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": decision.reason, "policy_decision_id": decision.policy_decision_id},
        )


@router.post("", response_model=ExperimentOut, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    req: ExperimentCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    current_user=Depends(get_current_user),
):
    redis = get_redis_pool()
    scope_key = None
    if idempotency_key:
        scope_key = build_scope_key(
            org_id=current_user.org_id,
            user_id=current_user.id,
            operation="experiments.create",
            resource_id=None,
            idempotency_key=idempotency_key,
        )
        state, cached = await prepare_request(
            redis,
            scope_key=scope_key,
            fingerprint=build_fingerprint(request.method, request.url.path, await request.body()),
        )
        if state == "replay" and cached is not None:
            return JSONResponse(status_code=cached["status_code"], content=cached["payload"])
        if state == "conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key already used with a different request payload",
            )
        if state == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request with this Idempotency-Key is still being processed",
            )

    svc = ExperimentService(db)
    exp = await svc.create(current_user.org_id, current_user.id, req)
    out = ExperimentOut.model_validate(exp)
    if scope_key:
        await store_response(
            redis,
            scope_key=scope_key,
            status_code=status.HTTP_201_CREATED,
            payload=out.model_dump(mode="json"),
        )
    return out


@router.get("/summary", response_model=ExperimentSummary)
async def get_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ExperimentService(db)
    return await svc.get_summary(current_user.org_id)


@router.get("", response_model=Page[ExperimentOut])
async def list_experiments(
    exp_status: Optional[ExperimentStatus] = Query(default=None, alias="status"),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = ExperimentService(db)
    exps, total = await svc.list(
        current_user.org_id,
        status=exp_status,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([ExperimentOut.model_validate(e) for e in exps], total, page_params)


@router.get("/{experiment_id}", response_model=ExperimentOut)
async def get_experiment(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ExperimentService(db)
    exp = await svc.get(current_user.org_id, experiment_id)
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return ExperimentOut.model_validate(exp)


@router.patch("/{experiment_id}", response_model=ExperimentOut)
async def update_experiment(
    experiment_id: UUID,
    req: ExperimentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ExperimentService(db)
    exp = await svc.update(current_user.org_id, experiment_id, req)
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return ExperimentOut.model_validate(exp)


@router.post("/{experiment_id}/transition", response_model=ExperimentOut)
async def transition_experiment(
    experiment_id: UUID,
    req: ExperimentTransition,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    session=Depends(get_session_context),
):
    svc = ExperimentService(db)
    exp = await svc.get(current_user.org_id, experiment_id)
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    action_map = {
        ExperimentStatus.APPROVED: "experiment.transition.approved",
        ExperimentStatus.RUNNING: "experiment.transition.running",
    }
    action = action_map.get(req.status, "experiment.transition.generic")
    high_risk = svc.is_high_risk(exp)
    approval_count = await svc.approval_count(current_user.org_id, experiment_id)
    await _evaluate_and_record_policy(
        db=db,
        current_user=current_user,
        session=session,
        response=response,
        action=action,
        experiment=exp,
        approval_count=approval_count,
        requires_dual_approval=high_risk,
    )

    try:
        exp = await svc.transition(current_user.org_id, experiment_id, req, approver_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ExperimentOut.model_validate(exp)


@router.post("/{experiment_id}/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    experiment_id: UUID,
    req: RunCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    session=Depends(get_session_context),
):
    svc = ExperimentService(db)
    exp = await svc.get(current_user.org_id, experiment_id)
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    await _evaluate_and_record_policy(
        db=db,
        current_user=current_user,
        session=session,
        response=response,
        action="experiment.run.create",
        experiment=exp,
        approval_count=await svc.approval_count(current_user.org_id, experiment_id),
        requires_dual_approval=svc.is_high_risk(exp),
    )
    try:
        run = await svc.create_run(current_user.org_id, experiment_id, req, actor_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return RunOut.model_validate(run)


@router.get("/{experiment_id}/runs", response_model=List[RunOut])
async def list_runs(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ExperimentService(db)
    runs = await svc.list_runs(current_user.org_id, experiment_id)
    return [RunOut.model_validate(r) for r in runs]


@router.patch("/{experiment_id}/runs/{run_id}", response_model=RunOut)
async def update_run(
    experiment_id: UUID,
    run_id: UUID,
    req: RunUpdate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    session=Depends(get_session_context),
):
    svc = ExperimentService(db)
    exp = await svc.get(current_user.org_id, experiment_id)
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    await _evaluate_and_record_policy(
        db=db,
        current_user=current_user,
        session=session,
        response=response,
        action="experiment.run.update",
        experiment=exp,
        approval_count=await svc.approval_count(current_user.org_id, experiment_id),
        requires_dual_approval=svc.is_high_risk(exp),
    )
    run = await svc.update_run(
        current_user.org_id,
        experiment_id,
        run_id,
        req,
        actor_user_id=current_user.id,
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunOut.model_validate(run)


@router.post("/{experiment_id}/approvals", response_model=ExperimentApprovalOut, status_code=status.HTTP_201_CREATED)
async def approve_experiment(
    experiment_id: UUID,
    req: ExperimentApprovalCreate,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    current_user=Depends(get_current_user),
    session=Depends(get_session_context),
):
    redis = get_redis_pool()
    scope_key = None
    if idempotency_key:
        scope_key = build_scope_key(
            org_id=current_user.org_id,
            user_id=current_user.id,
            operation="experiments.approve",
            resource_id=experiment_id,
            idempotency_key=idempotency_key,
        )
        state, cached = await prepare_request(
            redis,
            scope_key=scope_key,
            fingerprint=build_fingerprint(request.method, request.url.path, await request.body()),
        )
        if state == "replay" and cached is not None:
            return JSONResponse(status_code=cached["status_code"], content=cached["payload"])
        if state == "conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key already used with a different request payload",
            )
        if state == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request with this Idempotency-Key is still being processed",
            )

    svc = ExperimentService(db)
    exp = await svc.get(current_user.org_id, experiment_id)
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    await _evaluate_and_record_policy(
        db=db,
        current_user=current_user,
        session=session,
        response=response,
        action="experiment.transition.approved",
        experiment=exp,
        approval_count=await svc.approval_count(current_user.org_id, experiment_id),
        requires_dual_approval=svc.is_high_risk(exp),
    )
    try:
        approval = await svc.create_approval(current_user.org_id, experiment_id, current_user.id, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    out = ExperimentApprovalOut.model_validate(approval)
    if scope_key:
        await store_response(
            redis,
            scope_key=scope_key,
            status_code=status.HTTP_201_CREATED,
            payload=out.model_dump(mode="json"),
        )
    return out


@router.get("/{experiment_id}/approvals", response_model=List[ExperimentApprovalOut])
async def list_approvals(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ExperimentService(db)
    approvals = await svc.list_approvals(current_user.org_id, experiment_id)
    return [ExperimentApprovalOut.model_validate(a) for a in approvals]
