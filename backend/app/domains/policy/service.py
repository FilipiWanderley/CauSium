from __future__ import annotations
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.policy import PolicyDecision, SessionContext
from app.domains.audit_chain.service import AuditChainService
from app.domains.policy.models import PolicyBundle, PolicyDecisionEvidence


class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    async def get_active_bundle(self, org_id: UUID) -> PolicyBundle | None:
        result = await self.db.execute(
            select(PolicyBundle)
            .where(PolicyBundle.org_id == org_id, PolicyBundle.is_active.is_(True))
            .order_by(PolicyBundle.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def ensure_default_bundle(self, org_id: UUID) -> PolicyBundle:
        bundle = await self.get_active_bundle(org_id)
        if bundle:
            return bundle
        bundle = PolicyBundle(
            org_id=org_id,
            name="default-runtime-guardrails",
            version="1.0.0",
            engine="internal-pbac-abac",
            rules={
                "session_risk_block_high": True,
                "production_requires_maintenance_window": True,
                "critical_requires_low_session_risk": True,
                "high_risk_requires_dual_approval": True,
            },
            is_active=True,
        )
        self.db.add(bundle)
        await self.db.flush()
        await self.db.refresh(bundle)
        return bundle

    async def record_decision(
        self,
        *,
        org_id: UUID,
        actor_user_id: UUID | None,
        decision: PolicyDecision,
        session: SessionContext,
        action: str,
        resource_type: str,
        resource_id: str,
    ) -> PolicyDecisionEvidence:
        bundle = await self.ensure_default_bundle(org_id)
        evidence = PolicyDecisionEvidence(
            org_id=org_id,
            policy_bundle_id=bundle.id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            allowed=decision.allowed,
            reason=decision.reason,
            session_context={
                "session_risk": session.session_risk,
                "maintenance_window": session.maintenance_window,
                "geo_velocity_high": session.geo_velocity_high,
                "device_trusted": session.device_trusted,
            },
            policy_decision_id=decision.policy_decision_id,
        )
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="policy.decision.recorded",
            entity_type=resource_type,
            entity_id=resource_id,
            payload={
                "policy_decision_id": evidence.policy_decision_id,
                "action": evidence.action,
                "allowed": evidence.allowed,
                "policy_bundle_id": str(evidence.policy_bundle_id) if evidence.policy_bundle_id else None,
            },
        )
        return evidence
