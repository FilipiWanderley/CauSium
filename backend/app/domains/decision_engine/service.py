from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.decision_engine.models import (
    OptimizationOpportunity,
    OpportunityCategory,
    OpportunityStatus,
    RiskLevel,
)
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService
from app.domains.audit_chain.service import AuditChainService
from app.domains.decision_engine.schemas import (
    OpportunityCreate,
    OpportunitySummary,
    OpportunityStatusUpdate,
)
from app.domains.decision_engine.scorer import PLAYBOOKS, compute_score
from app.domains.decision_engine.aks_autoscaler_recommendation_engine import (
    decide_aks_autoscaler_recommendation,
)
from app.domains.decision_engine.aks_nodepool_rightsizing_engine import (
    decide_aks_nodepool_rightsizing,
)
from app.domains.decision_engine.confidence_calibration_service import CalibrationSnapshot, ConfidenceCalibrationService
from app.domains.decision_engine.vm_rightsizing_engine import decide_vm_rightsizing
from app.domains.intel.models import UsageObservation

log = get_logger(__name__)


def _fmt_brl(value: float | int | None) -> str:
    """Format a numeric value as BRL currency (R$ X.XXX)."""
    if value is None:
        return "R$ 0"
    v = float(value)
    if v == int(v):
        return f"R$ {int(v):,.0f}".replace(",", ".")
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass(frozen=True)
class AksNodePoolCandidate:
    cluster_id: str
    cluster_name: str
    node_pool_name: str
    node_count: int
    node_sku: str | None
    region: str
    cpu_p95: float
    memory_p95: float
    monthly_cost: float
    history_days: int
    owner_team: str
    environment: str
    allocated_cpu: float | None
    allocated_memory: float | None
    requested_cpu: float | None
    requested_memory: float | None
    is_system_pool: bool
    autoscaler_enabled: bool
    autoscaler_min_count: int | None
    autoscaler_max_count: int | None
    has_kube_system_workloads: bool
    has_critical_workloads: bool
    cpu_p95_stddev: float | None
    memory_p95_stddev: float | None


class DecisionEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_opportunities_for_account(
        self, org_id: UUID, account_id: UUID
    ) -> list[OptimizationOpportunity]:
        """Generate opportunities from ClickHouse cost data."""
        from app.core.clickhouse import execute_query

        try:
            rows = execute_query(
                """
                SELECT
                    service,
                    owner_team,
                    environment,
                    region,
                    sum(cost_usd) as monthly_cost,
                    argMax(resource_id, date) as resource_id,
                    argMax(resource_name, date) as resource_name,
                    argMax(sku_name, date) as sku_name,
                    count() as data_points
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND account_id = {account_id:String}
                  AND date >= today() - 30
                GROUP BY service, owner_team, environment, region
                HAVING monthly_cost > 50
                ORDER BY monthly_cost DESC
                LIMIT 50
                """,
                {"org_id": str(org_id), "account_id": str(account_id)},
            )
        except Exception as e:
            log.warning("decision_engine.cost_query.failed", error=str(e))
            rows = []

        # Load Azure Advisor recommendations for this account
        try:
            advisor_rows = execute_query(
                """
                SELECT
                    resource_id,
                    estimated_savings_usd,
                    savings_period,
                    short_description,
                    impact,
                    category AS advisor_category,
                    recommendation_id,
                    subscription_id
                FROM recommendation_facts
                WHERE org_id = {org_id:String}
                  AND account_id = {account_id:String}
                  AND category = 'Cost'
                  AND estimated_savings_usd > 0
                ORDER BY estimated_savings_usd DESC
                """,
                {"org_id": str(org_id), "account_id": str(account_id)},
            ) or []
        except Exception as e:
            log.warning("decision_engine.advisor_query.failed", error=str(e))
            advisor_rows = []

        advisor_by_resource: dict[str, dict] = {}
        for ar in advisor_rows:
            rid = (ar.get("resource_id") or "").lower()
            if rid and rid not in advisor_by_resource:
                advisor_by_resource[rid] = ar

        aks_candidates = await self.get_aks_nodepool_candidates(org_id=org_id, account_id=account_id)

        active_statuses = (
            OpportunityStatus.OPEN,
            OpportunityStatus.IN_PROGRESS,
            OpportunityStatus.VALIDATED,
        )
        existing_result = await self.db.execute(
            select(OptimizationOpportunity)
            .where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.account_id == account_id,
                OptimizationOpportunity.status.in_(active_statuses),
            )
            .order_by(OptimizationOpportunity.created_at.desc())
        )
        existing_items = list(existing_result.scalars().all())

        existing_by_key: dict[str, OptimizationOpportunity] = {}
        duplicate_existing: list[OptimizationOpportunity] = []
        for item in existing_items:
            key = _opportunity_dedupe_key(
                category=item.category,
                service=item.service,
                owner_team=item.owner_team,
                environment=item.environment,
                region=item.region,
                resource_id=item.resource_id,
                account_id=item.account_id,
            )
            if key in existing_by_key:
                duplicate_existing.append(item)
                continue
            existing_by_key[key] = item

        now = datetime.now(timezone.utc)
        opportunities: list[OptimizationOpportunity] = []
        seen_keys_in_run: set[str] = set()
        strategy_calibration = await ConfidenceCalibrationService(self.db).get_category_snapshots(
            org_id=org_id,
            categories={
                OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
                OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
            },
        )
        for row in rows:
            monthly_cost = float(row.get("monthly_cost", 0))
            service = str(row.get("service", "unknown"))
            env = str(row.get("environment", "unknown"))
            team = str(row.get("owner_team", "Sem equipe identificada"))
            resource_id = str(row.get("resource_id", ""))
            resource_name = str(row.get("resource_name", ""))
            sku_name = (row.get("sku_name") or "").strip()
            machine_family = _infer_machine_family(sku_name, resource_name, service)
            region = str(row.get("region", ""))

            # Determine category heuristically
            category = _classify_service(service)
            score_rationale = ""
            decision_evidence = None
            override_risk: RiskLevel | None = None
            if category == OpportunityCategory.RIGHTSIZING:
                usage_observations = await self._list_usage_observations(
                    org_id=org_id,
                    account_id=account_id,
                    resource_id=resource_id,
                )
                decision = decide_vm_rightsizing(
                    current_sku=sku_name or None,
                    current_monthly_cost=monthly_cost,
                    observations=usage_observations,
                )
                if not decision.recommend:
                    continue
                decision_evidence = decision.evidence
                estimated_savings = float(decision.evidence.get("estimated_savings") or 0.0)
                score_rationale = (
                    f"{decision.reason} "
                    f"Confiança: {decision.confidence:.2f}. "
                    f"Evidência: {decision.evidence}."
                )
                if decision.risk_level == "low":
                    override_risk = RiskLevel.LOW
                elif decision.risk_level == "medium":
                    override_risk = RiskLevel.MEDIUM
                else:
                    override_risk = RiskLevel.HIGH
            elif category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING:
                # AKS node pools are handled by a dedicated candidate query to avoid fallback parsing.
                continue
            else:
                # Try to match with an Advisor recommendation for this resource
                advisor_rec = advisor_by_resource.get(resource_id.lower())
                if advisor_rec is not None:
                    raw_savings = float(advisor_rec.get("estimated_savings_usd") or 0)
                    period = str(advisor_rec.get("savings_period") or "annual")
                    estimated_savings = round(raw_savings / 12.0, 2) if period == "annual" else round(raw_savings, 2)
                    if estimated_savings < 10:
                        continue
                    decision_evidence = {
                        "source": "azure_advisor",
                        "advisor_recommendation_id": advisor_rec.get("recommendation_id") or "",
                        "advisor_impact": advisor_rec.get("impact") or "",
                        "advisor_description": advisor_rec.get("short_description") or "",
                        "savings_period": period,
                        "raw_savings_value": raw_savings,
                        "estimated_savings": estimated_savings,
                        "current_monthly_cost": round(float(monthly_cost), 2),
                    }
                    score_rationale = (
                        f"Azure Advisor: {advisor_rec.get('short_description') or ''}. "
                        f"Impacto: {advisor_rec.get('impact') or 'N/A'}. "
                        f"Estimated savings: {_fmt_brl(estimated_savings)}/month (source: Advisor)."
                    )
                else:
                    # No Advisor data — skip (don't show heuristic estimates)
                    continue

            score = compute_score(
                category=category,
                monthly_savings_usd=estimated_savings,
                environment=env,
                override_risk=override_risk,
            )
            if not score_rationale:
                score_rationale = score.rationale

            description = _generate_description(category, service, monthly_cost, estimated_savings)
            if category == OpportunityCategory.RIGHTSIZING and decision_evidence:
                description = (
                    f"Current VM: {decision_evidence.get('current_sku')}. "
                    f"Usage p95: CPU {decision_evidence.get('cpu_p95')}% / memory {decision_evidence.get('memory_p95')}%. "
                    f"Recommendation: {decision_evidence.get('recommended_sku')}. "
                    f"Current cost: {_fmt_brl(decision_evidence.get('current_monthly_cost'))}/month. "
                    f"Estimated cost: {_fmt_brl(decision_evidence.get('estimated_monthly_cost'))}/month. "
                    f"Savings: {_fmt_brl(decision_evidence.get('estimated_savings'))}/month "
                    f"({decision_evidence.get('estimated_savings_pct')}%)."
                )
            elif category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING and decision_evidence:
                description = (
                    f"AKS {decision_evidence.get('cluster_name')}, node pool {decision_evidence.get('node_pool')}. "
                    f"Nodes: {decision_evidence.get('current_node_count')} -> "
                    f"{decision_evidence.get('recommended_node_count')}. "
                    f"Usage p95: CPU {decision_evidence.get('cpu_p95')}% / "
                    f"memory {decision_evidence.get('memory_p95')}%. "
                    f"Current cost: {_fmt_brl(decision_evidence.get('current_monthly_cost'))}/month. "
                    f"Estimated cost: {_fmt_brl(decision_evidence.get('estimated_monthly_cost'))}/month. "
                    f"Savings: {_fmt_brl(decision_evidence.get('estimated_savings'))}/month "
                    f"({decision_evidence.get('estimated_savings_pct')}%)."
                )
            elif decision_evidence and decision_evidence.get("source") == "azure_advisor":
                description = (
                    f"Azure Advisor: {decision_evidence.get('advisor_description')}. "
                    f"Current cost: {_fmt_brl(decision_evidence.get('current_monthly_cost'))}/month. "
                    f"Estimated savings: {_fmt_brl(estimated_savings)}/month "
                    f"(source: Azure Advisor, impact: {decision_evidence.get('advisor_impact')})."
                )

            dedupe_key = _opportunity_dedupe_key(
                category=category,
                service=service,
                owner_team=team,
                environment=env,
                region=region,
                resource_id=resource_id,
                account_id=account_id,
            )
            if dedupe_key in seen_keys_in_run:
                continue
            seen_keys_in_run.add(dedupe_key)

            existing = existing_by_key.get(dedupe_key)
            if existing is not None:
                existing.title = _generate_title(category, service, team)
                existing.description = description
                existing.category = category
                existing.financial_impact_score = score.financial_impact_score
                existing.risk_score = score.risk_score
                existing.effort_score = score.effort_score
                existing.criticality_score = score.criticality_score
                existing.composite_score = score.composite_score
                existing.estimated_monthly_savings_usd = estimated_savings
                existing.estimated_annual_savings_usd = round(estimated_savings * 12, 2)
                existing.current_monthly_cost_usd = monthly_cost
                existing.risk_level = score.risk_level
                existing.effort_level = score.effort_level
                existing.resource_id = resource_id
                existing.resource_name = resource_name
                existing.sku_name = sku_name or None
                existing.machine_family = machine_family
                existing.service = service
                existing.region = region
                existing.environment = env
                existing.owner_team = team
                existing.score_rationale = score_rationale
                existing.decision_evidence = decision_evidence
                existing.playbook = PLAYBOOKS.get(category)
                existing.detected_at = now
                op = existing
            else:
                op = OptimizationOpportunity(
                    org_id=org_id,
                    account_id=account_id,
                    title=_generate_title(category, service, team),
                    description=description,
                    category=category,
                    financial_impact_score=score.financial_impact_score,
                    risk_score=score.risk_score,
                    effort_score=score.effort_score,
                    criticality_score=score.criticality_score,
                    composite_score=score.composite_score,
                    estimated_monthly_savings_usd=estimated_savings,
                    estimated_annual_savings_usd=round(estimated_savings * 12, 2),
                    current_monthly_cost_usd=monthly_cost,
                    risk_level=score.risk_level,
                    effort_level=score.effort_level,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    sku_name=sku_name or None,
                    machine_family=machine_family,
                    service=service,
                    region=region,
                    environment=env,
                    owner_team=team,
                    score_rationale=score_rationale,
                    decision_evidence=decision_evidence,
                    playbook=PLAYBOOKS.get(category),
                )
                self.db.add(op)
                existing_by_key[dedupe_key] = op
            opportunities.append(op)

        for candidate in aks_candidates:
            service = "Azure Kubernetes Service"
            env = candidate.environment or "unknown"
            team = candidate.owner_team or "Sem equipe identificada"
            region = candidate.region or ""
            monthly_cost = float(candidate.monthly_cost)
            resource_id = _build_aks_nodepool_resource_id(
                cluster_id=candidate.cluster_id,
                node_pool_name=candidate.node_pool_name,
            )
            resource_name = f"{candidate.cluster_name}/{candidate.node_pool_name}"
            sku_name = candidate.node_sku or ""
            machine_family = _infer_machine_family(sku_name, resource_name, service)

            category = OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING
            autoscaler_category = OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION
            decision = decide_aks_nodepool_rightsizing(
                cluster_name=candidate.cluster_name,
                node_pool=candidate.node_pool_name,
                node_sku=candidate.node_sku,
                current_node_count=candidate.node_count,
                current_monthly_cost=monthly_cost,
                cpu_p95=candidate.cpu_p95,
                memory_p95=candidate.memory_p95,
                history_days=candidate.history_days,
                allocated_cpu=candidate.allocated_cpu,
                allocated_memory=candidate.allocated_memory,
                requested_cpu=candidate.requested_cpu,
                requested_memory=candidate.requested_memory,
                is_system_pool=candidate.is_system_pool,
                autoscaler_enabled=candidate.autoscaler_enabled,
                autoscaler_min_count=candidate.autoscaler_min_count,
                autoscaler_max_count=candidate.autoscaler_max_count,
                has_kube_system_workloads=candidate.has_kube_system_workloads,
                has_critical_workloads=candidate.has_critical_workloads,
                cpu_p95_stddev=candidate.cpu_p95_stddev,
                memory_p95_stddev=candidate.memory_p95_stddev,
            )
            autoscaler_decision = decide_aks_autoscaler_recommendation(
                cluster_name=candidate.cluster_name,
                node_pool=candidate.node_pool_name,
                node_sku=candidate.node_sku,
                current_node_count=candidate.node_count,
                current_monthly_cost=monthly_cost,
                cpu_p95=candidate.cpu_p95,
                memory_p95=candidate.memory_p95,
                history_days=candidate.history_days,
                autoscaler_enabled=candidate.autoscaler_enabled,
                autoscaler_min_count=candidate.autoscaler_min_count,
                autoscaler_max_count=candidate.autoscaler_max_count,
                is_system_pool=candidate.is_system_pool,
                has_kube_system_workloads=candidate.has_kube_system_workloads,
                has_critical_workloads=candidate.has_critical_workloads,
                cpu_p95_stddev=candidate.cpu_p95_stddev,
                memory_p95_stddev=candidate.memory_p95_stddev,
            )
            if not decision.recommend and not autoscaler_decision.recommend:
                continue

            adaptive = _resolve_adaptive_aks_strategy(
                rightsizing_recommended=decision.recommend,
                rightsizing_confidence=decision.confidence,
                autoscaler_recommended=autoscaler_decision.recommend,
                autoscaler_confidence=autoscaler_decision.confidence,
                cpu_p95=candidate.cpu_p95,
                memory_p95=candidate.memory_p95,
                variability_score=float(autoscaler_decision.evidence.get("variability_score") or 0.0),
                calibration_by_category=strategy_calibration,
            )

            if decision.recommend:
                decision_evidence = dict(decision.evidence or {})
                decision_evidence.update(adaptive["nodepool_rightsizing"])
                estimated_savings = float(decision_evidence.get("estimated_savings") or 0.0)
                adaptive_confidence = float(decision_evidence.get("confidence") or 0.0)
                score_rationale = (
                    f"{decision.reason} "
                    f"Confiança: {adaptive_confidence:.2f}. "
                    f"Evidência: {decision_evidence}."
                )
                if decision.risk_level == "low":
                    override_risk = RiskLevel.LOW
                elif decision.risk_level == "medium":
                    override_risk = RiskLevel.MEDIUM
                else:
                    override_risk = RiskLevel.HIGH
                score = compute_score(
                    category=category,
                    monthly_savings_usd=estimated_savings,
                    environment=env,
                    override_risk=override_risk,
                )
                description = (
                    f"AKS {decision_evidence.get('cluster_name')}, node pool {decision_evidence.get('node_pool')}. "
                    f"Nodes: {decision_evidence.get('current_node_count')} -> "
                    f"{decision_evidence.get('recommended_node_count')}. "
                    f"Usage p95: CPU {decision_evidence.get('cpu_p95')}% / "
                    f"memory {decision_evidence.get('memory_p95')}%. "
                    f"Current cost: {_fmt_brl(decision_evidence.get('current_monthly_cost'))}/month. "
                    f"Estimated cost: {_fmt_brl(decision_evidence.get('estimated_monthly_cost'))}/month. "
                    f"Savings: {_fmt_brl(decision_evidence.get('estimated_savings'))}/month "
                    f"({decision_evidence.get('estimated_savings_pct')}%). "
                    f"Recommended strategy: {decision_evidence.get('recommended_strategy')}."
                )
                dedupe_key = _opportunity_dedupe_key(
                    category=category,
                    service=service,
                    owner_team=team,
                    environment=env,
                    region=region,
                    resource_id=resource_id,
                    account_id=account_id,
                )
                if dedupe_key not in seen_keys_in_run:
                    seen_keys_in_run.add(dedupe_key)
                    existing = existing_by_key.get(dedupe_key)
                    if existing is not None:
                        existing.title = _generate_title(category, service, team)
                        existing.description = description
                        existing.category = category
                        existing.financial_impact_score = score.financial_impact_score
                        existing.risk_score = score.risk_score
                        existing.effort_score = score.effort_score
                        existing.criticality_score = score.criticality_score
                        existing.composite_score = score.composite_score
                        existing.estimated_monthly_savings_usd = estimated_savings
                        existing.estimated_annual_savings_usd = round(estimated_savings * 12, 2)
                        existing.current_monthly_cost_usd = monthly_cost
                        existing.risk_level = score.risk_level
                        existing.effort_level = score.effort_level
                        existing.resource_id = resource_id
                        existing.resource_name = resource_name
                        existing.sku_name = sku_name or None
                        existing.machine_family = machine_family
                        existing.service = service
                        existing.region = region
                        existing.environment = env
                        existing.owner_team = team
                        existing.score_rationale = score_rationale
                        existing.decision_evidence = decision_evidence
                        existing.playbook = PLAYBOOKS.get(category)
                        existing.detected_at = now
                        op = existing
                    else:
                        op = OptimizationOpportunity(
                            org_id=org_id,
                            account_id=account_id,
                            title=_generate_title(category, service, team),
                            description=description,
                            category=category,
                            financial_impact_score=score.financial_impact_score,
                            risk_score=score.risk_score,
                            effort_score=score.effort_score,
                            criticality_score=score.criticality_score,
                            composite_score=score.composite_score,
                            estimated_monthly_savings_usd=estimated_savings,
                            estimated_annual_savings_usd=round(estimated_savings * 12, 2),
                            current_monthly_cost_usd=monthly_cost,
                            risk_level=score.risk_level,
                            effort_level=score.effort_level,
                            resource_id=resource_id,
                            resource_name=resource_name,
                            sku_name=sku_name or None,
                            machine_family=machine_family,
                            service=service,
                            region=region,
                            environment=env,
                            owner_team=team,
                            score_rationale=score_rationale,
                            decision_evidence=decision_evidence,
                            playbook=PLAYBOOKS.get(category),
                        )
                        self.db.add(op)
                        existing_by_key[dedupe_key] = op
                    opportunities.append(op)

            if autoscaler_decision.recommend:
                autoscaler_evidence = dict(autoscaler_decision.evidence or {})
                autoscaler_evidence.update(adaptive["autoscaler"])
                autoscaler_savings = float(autoscaler_evidence.get("estimated_savings") or 0.0)
                autoscaler_confidence = float(autoscaler_evidence.get("confidence") or 0.0)
                autoscaler_score_rationale = (
                    f"{autoscaler_decision.reason} "
                    f"Confiança: {autoscaler_confidence:.2f}. "
                    f"Evidência: {autoscaler_evidence}."
                )
                if autoscaler_decision.risk_level == "low":
                    autoscaler_override_risk = RiskLevel.LOW
                elif autoscaler_decision.risk_level == "medium":
                    autoscaler_override_risk = RiskLevel.MEDIUM
                else:
                    autoscaler_override_risk = RiskLevel.HIGH
                autoscaler_score = compute_score(
                    category=autoscaler_category,
                    monthly_savings_usd=autoscaler_savings,
                    environment=env,
                    override_risk=autoscaler_override_risk,
                )
                autoscaler_description = (
                    f"AKS {autoscaler_evidence.get('cluster_name')}, node pool {autoscaler_evidence.get('node_pool')}. "
                    f"Autoscaler: disabled. Current: {autoscaler_evidence.get('current_node_count')} fixed nodes. "
                    f"Recommended: min={autoscaler_evidence.get('recommended_min_count')}, "
                    f"max={autoscaler_evidence.get('recommended_max_count')}. "
                    f"Usage p95: CPU {autoscaler_evidence.get('cpu_p95')}% / "
                    f"memory {autoscaler_evidence.get('memory_p95')}%. "
                    f"Conservative estimated savings: {_fmt_brl(autoscaler_evidence.get('estimated_savings'))}/month "
                    f"({autoscaler_evidence.get('estimated_savings_pct')}%). "
                    f"Recommended strategy: {autoscaler_evidence.get('recommended_strategy')}."
                )
                autoscaler_dedupe_key = _opportunity_dedupe_key(
                    category=autoscaler_category,
                    service=service,
                    owner_team=team,
                    environment=env,
                    region=region,
                    resource_id=resource_id,
                    account_id=account_id,
                )
                if autoscaler_dedupe_key in seen_keys_in_run:
                    continue
                seen_keys_in_run.add(autoscaler_dedupe_key)

                autoscaler_existing = existing_by_key.get(autoscaler_dedupe_key)
                if autoscaler_existing is not None:
                    autoscaler_existing.title = _generate_title(autoscaler_category, service, team)
                    autoscaler_existing.description = autoscaler_description
                    autoscaler_existing.category = autoscaler_category
                    autoscaler_existing.financial_impact_score = autoscaler_score.financial_impact_score
                    autoscaler_existing.risk_score = autoscaler_score.risk_score
                    autoscaler_existing.effort_score = autoscaler_score.effort_score
                    autoscaler_existing.criticality_score = autoscaler_score.criticality_score
                    autoscaler_existing.composite_score = autoscaler_score.composite_score
                    autoscaler_existing.estimated_monthly_savings_usd = autoscaler_savings
                    autoscaler_existing.estimated_annual_savings_usd = round(autoscaler_savings * 12, 2)
                    autoscaler_existing.current_monthly_cost_usd = monthly_cost
                    autoscaler_existing.risk_level = autoscaler_score.risk_level
                    autoscaler_existing.effort_level = autoscaler_score.effort_level
                    autoscaler_existing.resource_id = resource_id
                    autoscaler_existing.resource_name = resource_name
                    autoscaler_existing.sku_name = sku_name or None
                    autoscaler_existing.machine_family = machine_family
                    autoscaler_existing.service = service
                    autoscaler_existing.region = region
                    autoscaler_existing.environment = env
                    autoscaler_existing.owner_team = team
                    autoscaler_existing.score_rationale = autoscaler_score_rationale
                    autoscaler_existing.decision_evidence = autoscaler_evidence
                    autoscaler_existing.playbook = PLAYBOOKS.get(autoscaler_category)
                    autoscaler_existing.detected_at = now
                    autoscaler_op = autoscaler_existing
                else:
                    autoscaler_op = OptimizationOpportunity(
                        org_id=org_id,
                        account_id=account_id,
                        title=_generate_title(autoscaler_category, service, team),
                        description=autoscaler_description,
                        category=autoscaler_category,
                        financial_impact_score=autoscaler_score.financial_impact_score,
                        risk_score=autoscaler_score.risk_score,
                        effort_score=autoscaler_score.effort_score,
                        criticality_score=autoscaler_score.criticality_score,
                        composite_score=autoscaler_score.composite_score,
                        estimated_monthly_savings_usd=autoscaler_savings,
                        estimated_annual_savings_usd=round(autoscaler_savings * 12, 2),
                        current_monthly_cost_usd=monthly_cost,
                        risk_level=autoscaler_score.risk_level,
                        effort_level=autoscaler_score.effort_level,
                        resource_id=resource_id,
                        resource_name=resource_name,
                        sku_name=sku_name or None,
                        machine_family=machine_family,
                        service=service,
                        region=region,
                        environment=env,
                        owner_team=team,
                        score_rationale=autoscaler_score_rationale,
                        decision_evidence=autoscaler_evidence,
                        playbook=PLAYBOOKS.get(autoscaler_category),
                    )
                    self.db.add(autoscaler_op)
                    existing_by_key[autoscaler_dedupe_key] = autoscaler_op
                opportunities.append(autoscaler_op)

        for duplicated in duplicate_existing:
            if duplicated.status != OpportunityStatus.OPEN:
                continue
            duplicated.status = OpportunityStatus.DISMISSED
            duplicated.score_rationale = (
                (duplicated.score_rationale or "").strip()
                + "\n\n[system] Auto-dismissed duplicate opportunity."
            ).strip()

        # --- Standalone Advisor-backed opportunities (GROUPED) ---
        # Group Advisor recommendations by subscription + type to reduce visual noise.
        # Each group becomes one opportunity with child_recommendations in evidence.
        advisor_used_rids = {k.lower() for k in advisor_by_resource if k in seen_keys_in_run}

        # Step 1: Filter and collect eligible recommendations
        eligible_advisor: list[dict] = []
        seen_rec_ids: set[str] = set()
        for ar in advisor_rows:
            rid = (ar.get("resource_id") or "").strip()
            rec_id = ar.get("recommendation_id") or ""
            raw_savings = float(ar.get("estimated_savings_usd") or 0)
            if raw_savings <= 0:
                continue
            period = str(ar.get("savings_period") or "annual")
            monthly_savings = round(raw_savings / 12.0, 2) if period == "annual" else round(raw_savings, 2)
            if monthly_savings < 10:
                continue
            # Skip if already handled by cost_facts matching
            if rid.lower() in advisor_used_rids:
                continue
            # Dedupe within ClickHouse rows (multiple inserts create duplicates)
            if rec_id in seen_rec_ids:
                continue
            seen_rec_ids.add(rec_id)
            ar["_monthly_savings"] = monthly_savings
            ar["_period"] = period
            eligible_advisor.append(ar)

        # Step 2: Group by subscription_id + normalized recommendation type
        advisor_groups: dict[str, list[dict]] = {}
        for ar in eligible_advisor:
            sub_id = str(ar.get("subscription_id") or "")
            desc_lower = str(ar.get("short_description") or "").lower()
            norm_type = _normalize_advisor_type(desc_lower)
            group_key = f"{sub_id}|{norm_type}"
            advisor_groups.setdefault(group_key, []).append(ar)

        # Step 3: Create one opportunity per group
        for group_key, group_recs in advisor_groups.items():
            sub_id, norm_type = group_key.split("|", 1)

            # Sort by monthly savings descending — best option first
            group_recs.sort(key=lambda r: r["_monthly_savings"], reverse=True)
            best = group_recs[0]
            best_monthly = best["_monthly_savings"]
            best_rec_id = best.get("recommendation_id") or ""
            best_description = str(best.get("short_description") or "")
            best_impact = str(best.get("impact") or "Medium")
            best_rid = (best.get("resource_id") or "").strip()
            rec_count = len(group_recs)

            # Dedupe key for grouped opportunity
            advisor_dedupe_key = f"advisor_group|{_norm_text(str(account_id))}|{_norm_text(sub_id)}|{norm_type}"
            if advisor_dedupe_key in seen_keys_in_run:
                continue

            # Classify category and generate title
            category, title = _advisor_group_category_title(norm_type, sub_id, rec_count)

            # Build child recommendations list
            child_recommendations = [
                {
                    "recommendation_id": r.get("recommendation_id") or "",
                    "estimated_savings": r["_monthly_savings"],
                    "description": str(r.get("short_description") or ""),
                    "impact": str(r.get("impact") or "Medium"),
                    "resource_id": (r.get("resource_id") or "").strip(),
                }
                for r in group_recs
            ]

            decision_evidence = {
                "source": "azure_advisor",
                "is_grouped": True,
                "recommendation_count": rec_count,
                "best_recommendation_id": best_rec_id,
                "total_potential_savings": round(sum(r["_monthly_savings"] for r in group_recs), 2),
                "child_recommendations": child_recommendations,
                "subscription_id": sub_id,
                "advisor_description": best_description,
                "advisor_impact": best_impact,
                "savings_period": best.get("_period") or "annual",
                "estimated_savings": best_monthly,
                "estimated_annual_savings": round(best_monthly * 12, 2),
                "confidence": 0.90,
            }

            score = compute_score(
                category=category,
                monthly_savings_usd=best_monthly,
                environment="production",
                override_risk=RiskLevel.LOW,
            )

            if rec_count == 1:
                description = (
                    f"Azure Advisor: {best_description}. "
                    f"Estimated savings: {_fmt_brl(best_monthly)}/month ({_fmt_brl(round(best_monthly * 12, 2))}/year). "
                    f"Source: Azure Advisor, impact: {best_impact}."
                )
            else:
                description = (
                    f"Azure Advisor identified {rec_count} optimization options. "
                    f"Best option saves {_fmt_brl(best_monthly)}/month ({_fmt_brl(round(best_monthly * 12, 2))}/year). "
                    f"Source: Azure Advisor, impact: {best_impact}."
                )

            service = _extract_service_from_resource_id(best_rid) if best_rid else "Azure Subscription"
            resource_name = ""

            # Upsert: find existing grouped opportunity for same subscription + type
            existing_advisor = None
            for existing_key, existing_op in existing_by_key.items():
                ev = existing_op.decision_evidence or {}
                if (
                    ev.get("source") == "azure_advisor"
                    and ev.get("is_grouped") is True
                    and _norm_text(ev.get("subscription_id") or "") == _norm_text(sub_id)
                    and _normalize_advisor_type(str(ev.get("advisor_description") or "").lower()) == norm_type
                ):
                    existing_advisor = existing_op
                    break
            # Also match old non-grouped opportunities by best_recommendation_id
            if existing_advisor is None and best_rec_id:
                for existing_key, existing_op in existing_by_key.items():
                    ev = existing_op.decision_evidence or {}
                    if ev.get("source") == "azure_advisor" and ev.get("advisor_recommendation_id") == best_rec_id:
                        existing_advisor = existing_op
                        break

            if existing_advisor is not None:
                existing_advisor.title = title
                existing_advisor.description = description
                existing_advisor.category = category
                existing_advisor.financial_impact_score = score.financial_impact_score
                existing_advisor.risk_score = score.risk_score
                existing_advisor.effort_score = score.effort_score
                existing_advisor.criticality_score = score.criticality_score
                existing_advisor.composite_score = score.composite_score
                existing_advisor.estimated_monthly_savings_usd = best_monthly
                existing_advisor.estimated_annual_savings_usd = round(best_monthly * 12, 2)
                existing_advisor.risk_level = score.risk_level
                existing_advisor.effort_level = score.effort_level
                existing_advisor.resource_id = best_rid
                existing_advisor.resource_name = resource_name
                existing_advisor.service = service
                existing_advisor.score_rationale = score.rationale
                existing_advisor.decision_evidence = decision_evidence
                existing_advisor.detected_at = now
                op = existing_advisor
            else:
                op = OptimizationOpportunity(
                    org_id=org_id,
                    account_id=account_id,
                    title=title,
                    description=description,
                    category=category,
                    financial_impact_score=score.financial_impact_score,
                    risk_score=score.risk_score,
                    effort_score=score.effort_score,
                    criticality_score=score.criticality_score,
                    composite_score=score.composite_score,
                    estimated_monthly_savings_usd=best_monthly,
                    estimated_annual_savings_usd=round(best_monthly * 12, 2),
                    current_monthly_cost_usd=0.0,
                    risk_level=score.risk_level,
                    effort_level=score.effort_level,
                    resource_id=best_rid,
                    resource_name=resource_name,
                    service=service,
                    region="",
                    environment="production",
                    owner_team="Sem equipe identificada",
                    score_rationale=score.rationale,
                    decision_evidence=decision_evidence,
                    playbook=PLAYBOOKS.get(category),
                )
                self.db.add(op)

            seen_keys_in_run.add(advisor_dedupe_key)
            opportunities.append(op)

        await self.db.flush()
        log.info("decision_engine.generated", org_id=str(org_id), count=len(opportunities))
        return opportunities

    async def create_opportunity(self, org_id: UUID, req: OpportunityCreate) -> OptimizationOpportunity:
        score = compute_score(
            category=req.category,
            monthly_savings_usd=req.estimated_monthly_savings_usd,
            environment=req.environment,
            override_risk=req.risk_level,
            override_effort=req.effort_level,
        )
        op = OptimizationOpportunity(
            org_id=org_id,
            account_id=req.account_id,
            title=req.title,
            description=req.description,
            category=req.category,
            financial_impact_score=score.financial_impact_score,
            risk_score=score.risk_score,
            effort_score=score.effort_score,
            criticality_score=score.criticality_score,
            composite_score=score.composite_score,
            estimated_monthly_savings_usd=req.estimated_monthly_savings_usd,
            estimated_annual_savings_usd=round(req.estimated_monthly_savings_usd * 12, 2),
            current_monthly_cost_usd=req.current_monthly_cost_usd,
            risk_level=score.risk_level,
            effort_level=score.effort_level,
            resource_id=req.resource_id,
            resource_name=req.resource_name,
            sku_name=req.sku_name,
            machine_family=req.machine_family,
            service=req.service,
            region=req.region,
            environment=req.environment,
            owner_team=req.owner_team,
            score_rationale=score.rationale,
            playbook=PLAYBOOKS.get(req.category),
        )
        self.db.add(op)
        await self.db.flush()
        await self.db.refresh(op)

        notif = NotificationsService(self.db)
        await notif.create_realtime_alert(
            org_id=org_id,
            category=AlertCategory.OPTIMIZATION,
            severity=AlertSeverity.CRITICAL,
            event_type="opportunity.created",
            title=f"New optimization opportunity: {op.title}",
            body=op.description,
            source_type="optimization_opportunity",
            source_id=str(op.id),
            extra_metadata={
                "estimated_monthly_savings_usd": op.estimated_monthly_savings_usd,
                "category": op.category.value,
            },
        )
        return op

    async def list_opportunities(
        self,
        org_id: UUID,
        status: OpportunityStatus | None = None,
        category: OpportunityCategory | None = None,
        owner_team: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OptimizationOpportunity], int]:
        filters = [OptimizationOpportunity.org_id == org_id]
        if status:
            filters.append(OptimizationOpportunity.status == status)
        if category:
            filters.append(OptimizationOpportunity.category == category)
        if owner_team:
            filters.append(OptimizationOpportunity.owner_team == owner_team)

        count_result = await self.db.execute(
            select(func.count()).select_from(OptimizationOpportunity).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(OptimizationOpportunity)
            .where(*filters)
            .order_by(OptimizationOpportunity.composite_score.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def get_opportunity(self, org_id: UUID, opp_id: UUID) -> OptimizationOpportunity | None:
        result = await self.db.execute(
            select(OptimizationOpportunity).where(
                OptimizationOpportunity.id == opp_id,
                OptimizationOpportunity.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        org_id: UUID,
        opp_id: UUID,
        req: OpportunityStatusUpdate,
        *,
        actor_user_id: UUID | None = None,
    ) -> OptimizationOpportunity | None:
        op = await self.get_opportunity(org_id, opp_id)
        if not op:
            return None
        previous_status = op.status
        op.status = req.status
        await self._append_status_audit_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            opportunity=op,
            previous_status=previous_status,
            new_status=req.status,
        )
        await self.db.flush()
        await self.db.refresh(op)
        return op

    async def _append_status_audit_event(
        self,
        *,
        org_id: UUID,
        actor_user_id: UUID | None,
        opportunity: OptimizationOpportunity,
        previous_status: OpportunityStatus,
        new_status: OpportunityStatus,
    ) -> None:
        event_type, mapped_new_status = _map_status_to_audit_event(
            previous_status=previous_status,
            new_status=new_status,
        )
        if not event_type:
            return

        evidence = opportunity.decision_evidence or {}
        payload = {
            "opportunity_id": str(opportunity.id),
            "resource_id": opportunity.resource_name or opportunity.resource_id,
            "recommendation_type": opportunity.category.value.upper(),
            "previous_status": _status_alias(previous_status),
            "new_status": mapped_new_status,
            "estimated_savings_usd": float(opportunity.estimated_monthly_savings_usd or 0.0),
            "confidence": evidence.get("confidence"),
            "risk_level": evidence.get("risk_level") or opportunity.risk_level.value,
            "decision_evidence": evidence,
        }
        audit = AuditChainService(self.db)
        await audit.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type="optimization_opportunity",
            entity_id=str(opportunity.id),
            payload=payload,
        )

    async def get_summary(self, org_id: UUID) -> OpportunitySummary:
        result = await self.db.execute(
            select(
                func.count(OptimizationOpportunity.id).label("total"),
                func.sum(OptimizationOpportunity.estimated_monthly_savings_usd).label("total_savings"),
            ).where(OptimizationOpportunity.org_id == org_id)
        )
        row = result.one()
        total = row.total or 0
        total_savings = float(row.total_savings or 0)

        open_count = await self._count_by_status(org_id, OpportunityStatus.OPEN)
        in_progress = await self._count_by_status(org_id, OpportunityStatus.IN_PROGRESS)
        resolved = await self._count_by_status(org_id, OpportunityStatus.RESOLVED)

        top_cat_row = await self.db.execute(
            select(OptimizationOpportunity.category, func.count().label("cnt"))
            .where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == OpportunityStatus.OPEN,
            )
            .group_by(OptimizationOpportunity.category)
            .order_by(func.count().desc())
            .limit(1)
        )
        top_cat = top_cat_row.first()

        return OpportunitySummary(
            total=total,
            open=open_count,
            in_progress=in_progress,
            resolved=resolved,
            total_potential_savings_usd=total_savings,
            top_category=top_cat[0].value if top_cat else None,
        )

    async def _count_by_status(self, org_id: UUID, status: OpportunityStatus) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == status,
            )
        )
        return result.scalar() or 0

    async def _list_usage_observations(
        self,
        *,
        org_id: UUID,
        account_id: UUID,
        resource_id: str,
    ) -> list[dict]:
        if not resource_id:
            return []
        result = await self.db.execute(
            select(UsageObservation).where(
                UsageObservation.org_id == org_id,
                UsageObservation.account_id == account_id,
                UsageObservation.resource_id == resource_id,
            )
        )
        rows = list(result.scalars().all())
        out: list[dict] = []
        for row in rows:
            out.append(
                {
                    "metric_name": row.metric_name,
                    "p95_value": row.p95_value,
                    "window_start": row.window_start,
                }
            )
        return out

    async def get_aks_nodepool_candidates(
        self,
        *,
        org_id: UUID,
        account_id: UUID,
    ) -> list[AksNodePoolCandidate]:
        from app.core.clickhouse import execute_query

        try:
            rows = execute_query(
                """
                /* AKS_NODEPOOL_CANDIDATES */
                WITH
                    cost_by_pool AS (
                        SELECT
                            replaceRegexpOne(
                                resource_id,
                                '(?i)/agentPools/[^/]+$',
                                ''
                            ) AS cluster_id,
                            extract(resource_id, '(?i)/managedClusters/([^/]+)') AS cluster_name,
                            extract(resource_id, '(?i)/agentPools/([^/]+)') AS node_pool_name,
                            argMax(sku_name, date) AS node_sku,
                            argMax(region, date) AS region,
                            argMax(environment, date) AS environment,
                            argMax(owner_team, date) AS owner_team,
                            argMax(tags, date) AS tags,
                            sum(cost_usd) AS monthly_cost
                        FROM cost_facts
                        WHERE org_id = {org_id:String}
                          AND account_id = {account_id:String}
                          AND date >= today() - 30
                          AND lowerUTF8(provider) = 'azure'
                          AND (
                              positionCaseInsensitiveUTF8(service, 'aks') > 0
                              OR positionCaseInsensitiveUTF8(service, 'kubernetes') > 0
                          )
                          AND match(resource_id, '(?i).*/managedClusters/[^/]+/agentPools/[^/]+$')
                        GROUP BY cluster_id, cluster_name, node_pool_name
                        HAVING monthly_cost > 0
                    ),
                    usage_by_pool AS (
                        SELECT
                            replaceRegexpOne(
                                resource_id,
                                '(?i)/agentPools/[^/]+$',
                                ''
                            ) AS cluster_id,
                            extract(resource_id, '(?i)/managedClusters/([^/]+)') AS cluster_name,
                            extract(resource_id, '(?i)/agentPools/([^/]+)') AS node_pool_name,
                            quantileTDigestIf(
                                0.95
                            )(
                                metric_value,
                                positionCaseInsensitiveUTF8(metric_name, 'cpu') > 0
                            ) AS cpu_p95,
                            stddevPopIf(
                                metric_value,
                                positionCaseInsensitiveUTF8(metric_name, 'cpu') > 0
                            ) AS cpu_p95_stddev,
                            quantileTDigestIf(
                                0.95
                            )(
                                metric_value,
                                positionCaseInsensitiveUTF8(metric_name, 'memory') > 0
                            ) AS memory_p95,
                            stddevPopIf(
                                metric_value,
                                positionCaseInsensitiveUTF8(metric_name, 'memory') > 0
                            ) AS memory_p95_stddev,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) IN ('node count', 'nodecount')
                            ) AS node_count,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) = 'allocated cpu'
                            ) AS allocated_cpu,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) = 'allocated memory'
                            ) AS allocated_memory,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) = 'requested cpu'
                            ) AS requested_cpu,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) = 'requested memory'
                            ) AS requested_memory,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) IN ('critical workloads', 'critical_workloads')
                            ) AS critical_workloads,
                            maxIf(
                                metric_value,
                                lowerUTF8(metric_name) IN ('kube-system pods', 'kube_system_pods')
                            ) AS kube_system_pods,
                            uniqExactIf(
                                date,
                                positionCaseInsensitiveUTF8(metric_name, 'cpu') > 0
                            ) AS cpu_days,
                            uniqExactIf(
                                date,
                                positionCaseInsensitiveUTF8(metric_name, 'memory') > 0
                            ) AS memory_days
                        FROM usage_facts
                        WHERE org_id = {org_id:String}
                          AND account_id = {account_id:String}
                          AND date >= today() - 30
                          AND lowerUTF8(provider) = 'azure'
                          AND match(resource_id, '(?i).*/managedClusters/[^/]+/agentPools/[^/]+$')
                        GROUP BY cluster_id, cluster_name, node_pool_name
                    )
                SELECT
                    c.cluster_id AS cluster_id,
                    c.cluster_name AS cluster_name,
                    c.node_pool_name AS node_pool_name,
                    toInt32(round(u.node_count, 0)) AS node_count,
                    c.node_sku AS node_sku,
                    c.region AS region,
                    round(u.cpu_p95, 2) AS cpu_p95,
                    round(u.memory_p95, 2) AS memory_p95,
                    round(c.monthly_cost, 2) AS monthly_cost,
                    toInt32(least(u.cpu_days, u.memory_days)) AS history_days,
                    c.owner_team AS owner_team,
                    c.environment AS environment,
                    c.tags AS tags,
                    round(u.allocated_cpu, 2) AS allocated_cpu,
                    round(u.allocated_memory, 2) AS allocated_memory,
                    round(u.requested_cpu, 2) AS requested_cpu,
                    round(u.requested_memory, 2) AS requested_memory,
                    round(u.cpu_p95_stddev, 2) AS cpu_p95_stddev,
                    round(u.memory_p95_stddev, 2) AS memory_p95_stddev,
                    toInt32(round(u.critical_workloads, 0)) AS critical_workloads,
                    toInt32(round(u.kube_system_pods, 0)) AS kube_system_pods
                FROM cost_by_pool c
                INNER JOIN usage_by_pool u
                    ON c.cluster_id = u.cluster_id
                   AND c.cluster_name = u.cluster_name
                   AND c.node_pool_name = u.node_pool_name
                WHERE u.node_count > 0
                  AND isFinite(u.cpu_p95)
                  AND isFinite(u.memory_p95)
                ORDER BY c.monthly_cost DESC
                LIMIT 200
                """,
                {"org_id": str(org_id), "account_id": str(account_id)},
            )
        except Exception as e:
            log.warning("decision_engine.aks_candidates_query.failed", error=str(e))
            return []

        out: list[AksNodePoolCandidate] = []
        for row in rows:
            cluster_id = str(row.get("cluster_id") or "").strip()
            cluster_name = str(row.get("cluster_name") or "").strip()
            node_pool_name = str(row.get("node_pool_name") or "").strip()
            node_count = _coerce_int(row.get("node_count")) or 0
            cpu_p95 = _coerce_float(row.get("cpu_p95"))
            memory_p95 = _coerce_float(row.get("memory_p95"))
            monthly_cost = _coerce_float(row.get("monthly_cost")) or 0.0
            history_days = _coerce_int(row.get("history_days")) or 0
            tags = _to_str_dict(row.get("tags"))
            node_pool_lower = node_pool_name.lower()
            mode_label = _first_non_empty(
                tags,
                [
                    "kubernetes.azure.com/mode",
                    "aks_nodepool_mode",
                    "nodepool_mode",
                ],
            )
            is_system_pool = "system" in node_pool_lower or mode_label.lower() == "system"
            row_is_system = row.get("is_system_pool")
            if isinstance(row_is_system, bool):
                is_system_pool = row_is_system
            autoscaler_enabled = _parse_bool(
                _first_non_empty(
                    tags,
                    [
                        "cluster_autoscaler_enabled",
                        "autoscaler_enabled",
                        "k8s_autoscaler_enabled",
                    ],
                )
            )
            if isinstance(row.get("autoscaler_enabled"), bool):
                autoscaler_enabled = bool(row.get("autoscaler_enabled"))
            autoscaler_min_count = _parse_int(
                _first_non_empty(tags, ["autoscaler_min_count", "min_count", "nodepool_min_count"])
            )
            autoscaler_min_count = autoscaler_min_count or _coerce_int(row.get("autoscaler_min_count"))
            autoscaler_max_count = _parse_int(
                _first_non_empty(tags, ["autoscaler_max_count", "max_count", "nodepool_max_count"])
            )
            autoscaler_max_count = autoscaler_max_count or _coerce_int(row.get("autoscaler_max_count"))
            has_critical_workloads = (_coerce_int(row.get("critical_workloads")) or 0) > 0
            has_kube_system_workloads = (_coerce_int(row.get("kube_system_pods")) or 0) > 0
            if isinstance(row.get("has_critical_workloads"), bool):
                has_critical_workloads = bool(row.get("has_critical_workloads"))
            if isinstance(row.get("has_kube_system_workloads"), bool):
                has_kube_system_workloads = bool(row.get("has_kube_system_workloads"))
            if not cluster_id or not cluster_name or not node_pool_name:
                continue
            if node_count <= 0:
                continue
            if cpu_p95 is None or memory_p95 is None:
                continue
            out.append(
                AksNodePoolCandidate(
                    cluster_id=cluster_id,
                    cluster_name=cluster_name,
                    node_pool_name=node_pool_name,
                    node_count=node_count,
                    node_sku=(str(row.get("node_sku") or "").strip() or None),
                    region=str(row.get("region") or "").strip(),
                    cpu_p95=cpu_p95,
                    memory_p95=memory_p95,
                    monthly_cost=monthly_cost,
                    history_days=history_days,
                    owner_team=str(row.get("owner_team") or "Sem equipe identificada").strip() or "Sem equipe identificada",
                    environment=str(row.get("environment") or "unknown").strip() or "unknown",
                    allocated_cpu=_coerce_float(row.get("allocated_cpu")),
                    allocated_memory=_coerce_float(row.get("allocated_memory")),
                    requested_cpu=_coerce_float(row.get("requested_cpu")),
                    requested_memory=_coerce_float(row.get("requested_memory")),
                    is_system_pool=is_system_pool,
                    autoscaler_enabled=autoscaler_enabled,
                    autoscaler_min_count=autoscaler_min_count,
                    autoscaler_max_count=autoscaler_max_count,
                    has_kube_system_workloads=has_kube_system_workloads,
                    has_critical_workloads=has_critical_workloads,
                    cpu_p95_stddev=_coerce_float(row.get("cpu_p95_stddev")),
                    memory_p95_stddev=_coerce_float(row.get("memory_p95_stddev")),
                )
            )
        return out


# ── Heuristics ────────────────────────────────────────────────────────────────

def _classify_service(service: str) -> OpportunityCategory:
    s = service.lower()
    if any(k in s for k in ("kubernetes", "aks")):
        return OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING
    if any(k in s for k in ("virtual machine", "compute")):
        return OpportunityCategory.RIGHTSIZING
    if any(k in s for k in ("storage", "blob", "disk")):
        return OpportunityCategory.STORAGE_OPTIMIZATION
    if any(k in s for k in ("bandwidth", "network", "cdn")):
        return OpportunityCategory.NETWORK_OPTIMIZATION
    if any(k in s for k in ("sql", "database", "cosmos")):
        return OpportunityCategory.RIGHTSIZING
    if any(k in s for k in ("function", "app service")):
        return OpportunityCategory.IDLE_RESOURCES
    return OpportunityCategory.IDLE_RESOURCES


def _status_alias(status: OpportunityStatus) -> str:
    if status == OpportunityStatus.OPEN:
        return "detected"
    return status.value


def _map_status_to_audit_event(
    *,
    previous_status: OpportunityStatus,
    new_status: OpportunityStatus,
) -> tuple[str | None, str | None]:
    if new_status == OpportunityStatus.RESOLVED:
        return "opportunity.accepted", "accepted"
    if new_status == OpportunityStatus.DISMISSED:
        if previous_status == OpportunityStatus.OPEN:
            return "opportunity.ignored", "ignored"
        return "opportunity.dismissed", "dismissed"
    return None, None


def _estimate_savings(category: OpportunityCategory, monthly_cost: float) -> float:
    rates = {
        OpportunityCategory.IDLE_RESOURCES: 0.80,
        OpportunityCategory.RIGHTSIZING: 0.30,
        OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: 0.20,
        OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: 0.18,
        OpportunityCategory.STORAGE_OPTIMIZATION: 0.40,
        OpportunityCategory.NETWORK_OPTIMIZATION: 0.25,
        OpportunityCategory.RESERVED_INSTANCES: 0.35,
        OpportunityCategory.LICENSE_OPTIMIZATION: 0.20,
        OpportunityCategory.ARCHITECTURE_CHANGE: 0.45,
    }
    return round(monthly_cost * rates.get(category, 0.20), 2)


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _resolve_adaptive_aks_strategy(
    *,
    rightsizing_recommended: bool,
    rightsizing_confidence: float,
    autoscaler_recommended: bool,
    autoscaler_confidence: float,
    cpu_p95: float,
    memory_p95: float,
    variability_score: float,
    calibration_by_category: dict[OpportunityCategory, CalibrationSnapshot],
) -> dict[str, dict[str, float | bool | str | None]]:
    rightsizing_calibration = calibration_by_category.get(OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING)
    autoscaler_calibration = calibration_by_category.get(OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION)

    rightsizing_accuracy = (
        float(rightsizing_calibration.historical_accuracy) if rightsizing_calibration is not None else None
    )
    autoscaler_accuracy = (
        float(autoscaler_calibration.historical_accuracy) if autoscaler_calibration is not None else None
    )
    rightsizing_adjustment = (
        float(rightsizing_calibration.confidence_adjustment) if rightsizing_calibration is not None else 0.0
    )
    autoscaler_adjustment = (
        float(autoscaler_calibration.confidence_adjustment) if autoscaler_calibration is not None else 0.0
    )

    rightsizing_history_bonus = ((rightsizing_accuracy - 0.5) * 0.10) if rightsizing_accuracy is not None else 0.0
    autoscaler_history_bonus = ((autoscaler_accuracy - 0.5) * 0.10) if autoscaler_accuracy is not None else 0.0
    rightsizing_context_bonus = 0.03 if cpu_p95 <= 35.0 and memory_p95 <= 50.0 else 0.0
    autoscaler_context_bonus = 0.04 if variability_score >= 0.55 else 0.0

    rightsizing_score = (
        _clamp_01(rightsizing_confidence + rightsizing_adjustment + rightsizing_history_bonus + rightsizing_context_bonus)
        if rightsizing_recommended
        else 0.0
    )
    autoscaler_score = (
        _clamp_01(autoscaler_confidence + autoscaler_adjustment + autoscaler_history_bonus + autoscaler_context_bonus)
        if autoscaler_recommended
        else 0.0
    )

    recommended_strategy = "none"
    alternative_strategy: str | None = None
    if rightsizing_recommended and autoscaler_recommended:
        if autoscaler_score >= rightsizing_score:
            recommended_strategy = "autoscaler"
            alternative_strategy = "nodepool_rightsizing"
        else:
            recommended_strategy = "nodepool_rightsizing"
            alternative_strategy = "autoscaler"
    elif rightsizing_recommended:
        recommended_strategy = "nodepool_rightsizing"
    elif autoscaler_recommended:
        recommended_strategy = "autoscaler"

    winner_boost = 0.08 if rightsizing_recommended and autoscaler_recommended else 0.0
    loser_penalty = -0.05 if rightsizing_recommended and autoscaler_recommended else 0.0
    rightsizing_final = rightsizing_confidence
    autoscaler_final = autoscaler_confidence
    if recommended_strategy == "nodepool_rightsizing":
        rightsizing_final = _clamp_01(rightsizing_confidence + winner_boost)
        if autoscaler_recommended:
            autoscaler_final = _clamp_01(autoscaler_confidence + loser_penalty)
    elif recommended_strategy == "autoscaler":
        autoscaler_final = _clamp_01(autoscaler_confidence + winner_boost)
        if rightsizing_recommended:
            rightsizing_final = _clamp_01(rightsizing_confidence + loser_penalty)

    return {
        "nodepool_rightsizing": {
            "confidence": round(rightsizing_final, 4),
            "recommended_strategy": recommended_strategy,
            "alternative_strategy": alternative_strategy,
            "confidence_boosted": recommended_strategy == "nodepool_rightsizing" and winner_boost > 0,
            "strategy_score": round(rightsizing_score, 4),
            "historical_accuracy": round(rightsizing_accuracy, 4) if rightsizing_accuracy is not None else None,
            "confidence_adjustment": round(rightsizing_adjustment, 4),
        },
        "autoscaler": {
            "confidence": round(autoscaler_final, 4),
            "recommended_strategy": recommended_strategy,
            "alternative_strategy": alternative_strategy,
            "confidence_boosted": recommended_strategy == "autoscaler" and winner_boost > 0,
            "strategy_score": round(autoscaler_score, 4),
            "historical_accuracy": round(autoscaler_accuracy, 4) if autoscaler_accuracy is not None else None,
            "confidence_adjustment": round(autoscaler_adjustment, 4),
        },
    }


def _generate_title(category: OpportunityCategory, service: str, team: str) -> str:
    titles = {
        OpportunityCategory.IDLE_RESOURCES: f"Idle {service} resources in team {team}",
        OpportunityCategory.RIGHTSIZING: f"Rightsize {service} for team {team}",
        OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: f"Rightsize AKS node pool for team {team}",
        OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: f"Enable AKS autoscaler for team {team}",
        OpportunityCategory.STORAGE_OPTIMIZATION: f"Optimize {service} storage tier",
        OpportunityCategory.NETWORK_OPTIMIZATION: f"Reduce {service} network costs",
        OpportunityCategory.RESERVED_INSTANCES: f"Purchase Reserved Instances for {service}",
        OpportunityCategory.LICENSE_OPTIMIZATION: f"Optimize {service} licenses",
        OpportunityCategory.ARCHITECTURE_CHANGE: f"Architectural optimization for {service}",
    }
    return titles.get(category, f"Optimize {service}")


def _generate_description(
    category: OpportunityCategory, service: str, monthly_cost: float, estimated_savings: float
) -> str:
    rate = estimated_savings / monthly_cost * 100 if monthly_cost else 0
    return (
        f"{service} is currently costing {_fmt_brl(monthly_cost)}/month. "
        f"Analysis indicates a {rate:.0f}% cost reduction opportunity ({_fmt_brl(estimated_savings)}/month) "
        f"through {category.value.replace('_', ' ')}."
    )


def _extract_family_token(raw_value: str) -> str | None:
    value = (raw_value or "").strip()
    if not value:
        return None

    normalized = re.sub(r"^standard[_-]", "", value, flags=re.IGNORECASE)
    normalized = normalized.strip()
    if not normalized:
        return None

    # AWS-style (e.g., m5.large -> m5) and GCP-style (e.g., n2-standard-4 -> n2).
    dotted_prefix = re.match(r"^([a-z]\d+)\.", normalized, flags=re.IGNORECASE)
    if dotted_prefix:
        return dotted_prefix.group(1).lower()
    hyphen_prefix = re.match(r"^([a-z]\d+)-", normalized, flags=re.IGNORECASE)
    if hyphen_prefix:
        return hyphen_prefix.group(1).lower()

    # Azure-style (e.g., Standard_D4s_v5 -> D4s).
    token_match = re.search(r"\b([A-Za-z]+\d+[A-Za-z0-9]*)\b", normalized)
    if token_match:
        return token_match.group(1)

    return None


def _infer_machine_family(sku_name: str | None, resource_name: str | None, service: str | None) -> str | None:
    for candidate in (sku_name or "", resource_name or "", service or ""):
        token = _extract_family_token(candidate)
        if token:
            return token
    return None


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _to_str_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in value.items():
        key = str(k or "").strip()
        if not key:
            continue
        out[key] = str(v or "").strip()
    return out


def _first_non_empty(tags: dict[str, str], keys: list[str]) -> str:
    lowered = {k.lower(): v for k, v in tags.items()}
    for key in keys:
        value = lowered.get(key.lower(), "").strip()
        if value:
            return value
    return ""


def _parse_bool(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"1", "true", "yes", "y", "enabled", "on"}


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def _build_aks_nodepool_resource_id(*, cluster_id: str, node_pool_name: str) -> str:
    normalized_cluster_id = (cluster_id or "").strip().lower().rstrip("/")
    normalized_pool = (node_pool_name or "").strip().lower()
    return f"aks:{normalized_cluster_id}:{normalized_pool}"


def _norm_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _norm_uuid(value: UUID | None) -> str:
    return str(value) if value is not None else ""


def _norm_resource_id(value: str | None) -> str:
    return _norm_text(value).rstrip("/")


def _extract_service_from_resource_id(resource_id: str) -> str:
    """Extract the Azure service name from an ARM resource ID."""
    lower = resource_id.lower()
    if "/providers/" not in lower:
        return "Azure Subscription"
    parts = lower.split("/providers/")
    if len(parts) < 2:
        return "Azure Subscription"
    provider_segment = parts[-1]
    segments = provider_segment.split("/")
    if len(segments) >= 2:
        return segments[0] + "/" + segments[1]
    return segments[0] if segments else "Azure"


def _normalize_advisor_type(desc_lower: str) -> str:
    """Normalize Advisor short_description to a grouping key."""
    if "savings plan" in desc_lower or "saving plan" in desc_lower:
        return "savings_plan"
    if "reserved" in desc_lower or "reservation" in desc_lower:
        return "reserved_instance"
    if "shut down" in desc_lower or "idle" in desc_lower or "deallocate" in desc_lower:
        return "idle_resource"
    if "right-size" in desc_lower or "rightsize" in desc_lower or "resize" in desc_lower:
        return "rightsizing"
    # Fallback: normalize the description itself as the type key
    normalized = re.sub(r"[^a-z0-9]+", "_", desc_lower[:50]).strip("_")
    return normalized or "other"


def _advisor_group_category_title(
    norm_type: str, subscription_id: str, rec_count: int
) -> tuple[OpportunityCategory, str]:
    """Return (category, title) for a grouped Advisor opportunity."""
    sub_display = f"{subscription_id[:8]}..."
    count_suffix = f" ({rec_count} options)" if rec_count > 1 else ""

    if norm_type == "savings_plan":
        return (
            OpportunityCategory.RESERVED_INSTANCES,
            f"Azure Savings Plan for subscription {sub_display}{count_suffix}",
        )
    if norm_type == "reserved_instance":
        return (
            OpportunityCategory.RESERVED_INSTANCES,
            f"Reserved Instance coverage for subscription {sub_display}{count_suffix}",
        )
    if norm_type == "idle_resource":
        return (
            OpportunityCategory.IDLE_RESOURCES,
            f"Idle resources in subscription {sub_display}{count_suffix}",
        )
    if norm_type == "rightsizing":
        return (
            OpportunityCategory.RIGHTSIZING,
            f"Rightsizing opportunities in subscription {sub_display}{count_suffix}",
        )
    return (
        OpportunityCategory.ARCHITECTURE_CHANGE,
        f"Azure Advisor: cost optimization for subscription {sub_display}{count_suffix}",
    )


def _opportunity_dedupe_key(
    *,
    category: OpportunityCategory,
    service: str | None,
    owner_team: str | None,
    environment: str | None,
    region: str | None,
    resource_id: str | None,
    account_id: UUID | None,
) -> str:
    # A stable identity for "same optimization target" across scoring runs.
    return "|".join(
        [
            _norm_uuid(account_id),
            category.value,
            _norm_resource_id(resource_id),
            _norm_text(service),
            _norm_text(owner_team),
            _norm_text(environment),
            _norm_text(region),
        ]
    )
