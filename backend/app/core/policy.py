from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.domains.auth.models import UserRole


@dataclass
class SessionContext:
    session_risk: str
    maintenance_window: bool
    geo_velocity_high: bool
    device_trusted: bool


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    policy_decision_id: str


def build_session_context(
    *,
    session_risk: str | None,
    maintenance_window: str | None,
    geo_velocity_high: str | None,
    device_trusted: str | None,
) -> SessionContext:
    normalized_risk = (session_risk or "medium").strip().lower()
    if normalized_risk not in {"low", "medium", "high"}:
        normalized_risk = "medium"
    return SessionContext(
        session_risk=normalized_risk,
        maintenance_window=(maintenance_window or "").strip().lower() in {"1", "true", "yes", "y", "on"},
        geo_velocity_high=(geo_velocity_high or "").strip().lower() in {"1", "true", "yes", "y", "on"},
        device_trusted=(device_trusted or "true").strip().lower() in {"1", "true", "yes", "y", "on"},
    )


def authorize_experiment_action(
    *,
    action: str,
    role: UserRole,
    environment: str,
    criticality: str,
    session: SessionContext,
    requires_dual_approval: bool,
    approval_count: int,
) -> PolicyDecision:
    decision_id = str(uuid4())
    env = (environment or "unknown").lower()
    crit = (criticality or "medium").lower()
    role_value = role.value if isinstance(role, UserRole) else str(role)

    if role_value == UserRole.VIEWER.value:
        return PolicyDecision(False, "viewer role cannot execute critical actions", decision_id)

    if session.session_risk == "high":
        return PolicyDecision(False, "session risk is high", decision_id)

    if session.geo_velocity_high and action in {"experiment.transition.running", "experiment.run.create"}:
        return PolicyDecision(False, "geo-velocity risk is high for this action", decision_id)

    if not session.device_trusted and action in {"experiment.transition.running", "experiment.run.create"}:
        return PolicyDecision(False, "untrusted device for runtime action", decision_id)

    if action in {"experiment.transition.approved", "experiment.transition.running"} and role_value not in {
        UserRole.ADMIN.value,
        UserRole.ENGINEER.value,
    }:
        return PolicyDecision(False, "role not allowed for approval or execution transition", decision_id)

    if action in {"experiment.run.create", "experiment.run.update"} and role_value not in {
        UserRole.ADMIN.value,
        UserRole.ENGINEER.value,
    }:
        return PolicyDecision(False, "role not allowed for run execution", decision_id)

    if env == "production" and action in {"experiment.transition.running", "experiment.run.create"}:
        if not session.maintenance_window:
            return PolicyDecision(False, "production execution requires maintenance window", decision_id)

    if crit in {"critical", "tier0", "tier-0"} and session.session_risk != "low":
        return PolicyDecision(False, "critical assets require low session risk", decision_id)

    if requires_dual_approval and action == "experiment.transition.running":
        if approval_count < 2:
            return PolicyDecision(False, "high-risk experiment requires at least two approvals", decision_id)

    return PolicyDecision(
        True,
        f"authorized action={action} env={env} criticality={crit} at={datetime.now(timezone.utc).isoformat()}",
        decision_id,
    )
