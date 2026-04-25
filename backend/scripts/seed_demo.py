"""
seed_demo.py — Popula dados ficticios realistas para apresentacao local.

Execucao:
    docker exec -it stratopulse-backend-1 python scripts/seed_demo.py
    python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
for candidate in ("/app", BACKEND_ROOT):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import ensure_workspace_keyring, hash_password

settings = get_settings()
rng = random.Random(42)

# ── constants ──────────────────────────────────────────────────────────────────

DEMO_ORG_ID = uuid.UUID("429cfe60-1d95-413e-ad7e-bccb4a76af3b")
DEMO_USER_ID = uuid.UUID("73cbbca3-1c75-4959-ab88-e37ef37839ee")
DEMO_ORG_NAME = "CauSium Demo Workspace"
DEMO_ORG_SLUG = "causium-demo-workspace"
DEMO_PLAN = "enterprise"
DEMO_USER_EMAIL = "demo@causium.dev"
DEMO_USER_NAME = "CauSium Demo Admin"
DEMO_USER_PASSWORD = "Demo@123456"

SERVICES   = ["Virtual Machines", "Azure Kubernetes Service", "Azure SQL Database",
               "Azure Storage", "Azure Functions", "App Service",
               "Azure Cache for Redis", "Azure Monitor", "Bandwidth", "Azure Cosmos DB"]
REGIONS    = ["eastus", "westeurope", "brazilsouth", "eastus2", "southeastasia"]
ENVS       = ["production", "staging", "development"]
TEAMS      = ["platform", "backend", "data", "frontend", "security", "infra"]
RESOURCE_TYPES = [
    "Microsoft.Compute/virtualMachines",
    "Microsoft.Sql/servers/databases",
    "Microsoft.Storage/storageAccounts",
    "Microsoft.ContainerService/managedClusters",
    "Microsoft.Web/sites",
    "Microsoft.Cache/Redis",
    "Microsoft.KeyVault/vaults",
    "Microsoft.Network/virtualNetworks",
]

TODAY      = date.today()
START_DATE = TODAY - timedelta(days=90)

SUB_ID     = "sub-nimbusops-prod-001"
_CLICKHOUSE_AVAILABLE: bool | None = None


# ══════════════════════════════════════════════════════════════════════════════
# PostgreSQL helpers
# ══════════════════════════════════════════════════════════════════════════════

def make_engine():
    return create_async_engine(settings.database_url, echo=False)


def _insert_rows_safe(table_name: str, rows: list[dict]) -> bool:
    global _CLICKHOUSE_AVAILABLE
    if _CLICKHOUSE_AVAILABLE is False:
        return False

    try:
        from app.core.clickhouse import insert_rows  # noqa: WPS433 - lazy import by design
    except ModuleNotFoundError as exc:
        if exc.name == "clickhouse_connect":
            if _CLICKHOUSE_AVAILABLE is not False:
                print("  ! clickhouse_connect nao instalado; seed de ClickHouse sera ignorado")
            _CLICKHOUSE_AVAILABLE = False
            return False
        raise

    _CLICKHOUSE_AVAILABLE = True
    insert_rows(table_name, rows)
    return True


async def ensure_demo_workspace(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    import app.domains.cloud_accounts.models  # noqa: F401 - ensure mapper registry
    from app.domains.auth.models import Organization, User, UserRole

    org_result = await session.execute(
        select(Organization).where(
            (Organization.id == DEMO_ORG_ID) | (Organization.slug == DEMO_ORG_SLUG)
        )
    )
    org = org_result.scalars().first()
    if not org:
        org = Organization(
            id=DEMO_ORG_ID,
            name=DEMO_ORG_NAME,
            slug=DEMO_ORG_SLUG,
            plan=DEMO_PLAN,
            is_active=True,
        )
        session.add(org)
        await session.flush()
        print(f"  ✓ workspace demo criado: {org.id}")
    else:
        org.name = DEMO_ORG_NAME
        org.slug = DEMO_ORG_SLUG
        org.plan = DEMO_PLAN
        org.is_active = True
        print(f"  · workspace demo existente: {org.id}")

    await ensure_workspace_keyring(session, org.id)

    user_result = await session.execute(
        select(User).where((User.id == DEMO_USER_ID) | (User.email == DEMO_USER_EMAIL))
    )
    user = user_result.scalars().first()
    if not user:
        user = User(
            id=DEMO_USER_ID,
            org_id=org.id,
            email=DEMO_USER_EMAIL,
            full_name=DEMO_USER_NAME,
            hashed_password=hash_password(DEMO_USER_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=False,
            password_changed_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.flush()
        print(f"  ✓ usuario demo criado: {user.email}")
    else:
        user.org_id = org.id
        user.email = DEMO_USER_EMAIL
        user.full_name = DEMO_USER_NAME
        user.role = UserRole.ADMIN
        user.is_active = True
        user.must_change_password = False
        user.hashed_password = hash_password(DEMO_USER_PASSWORD)
        user.password_changed_at = datetime.now(timezone.utc)
        print(f"  · usuario demo atualizado: {user.email}")

    await session.flush()
    return org.id, user.id


async def seed_postgres(session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID:
    import app.domains.admin.models  # noqa: F401 - registers Organization in mapper
    from app.domains.cloud_accounts.models import CloudAccount, CloudProvider, ConnectorStatus
    from app.domains.decision_engine.models import (
        EffortLevel, OpportunityCategory, OptimizationOpportunity,
        RiskLevel, OpportunityStatus,
    )
    from app.domains.workflow.models import Initiative, InitiativeStatus

    # ── 1. Cloud account ────────────────────────────────────────────────────
    existing = await session.execute(
        select(CloudAccount).where(CloudAccount.org_id == org_id)
    )
    account = existing.scalars().first()

    if not account:
        account = CloudAccount(
            id=uuid.uuid4(),
            org_id=org_id,
            provider=CloudProvider.AZURE,
            external_id=SUB_ID,
            display_name="CauSium Demo Azure Subscription",
            tenant_id="tenant-nimbusops-demo",
            status=ConnectorStatus.ACTIVE,
            last_sync_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        session.add(account)
        await session.flush()
        print(f"  ✓ cloud_account criada: {account.id}")
    else:
        print(f"  · cloud_account existente: {account.id}")

    account_id = account.id

    # ── 2. Optimization opportunities + initiatives (idempotente) ─────────
    await session.execute(
        delete(Initiative).where(Initiative.org_id == org_id)
    )
    await session.execute(
        delete(OptimizationOpportunity).where(OptimizationOpportunity.org_id == org_id)
    )
    await session.flush()

    OPPS = [
        {
            "title": "VM rightsizing - API workers de producao",
            "description": "Instancias Standard_D8s_v3 operam com baixa utilizacao. Recomendado reduzir para Standard_D4s_v3.",
            "category": OpportunityCategory.RIGHTSIZING,
            "risk_level": RiskLevel.LOW,
            "effort_level": EffortLevel.LOW,
            "monthly": 4200.0,
            "annual": 50400.0,
            "current": 9100.0,
            "score": 0.87,
            "status": OpportunityStatus.OPEN,
            "service": "Virtual Machines",
            "environment": "production",
            "owner_team": "platform",
            "resource_name": "vm-api-workers-prod",
            "resource_id": _make_resource_id("platform", "Microsoft.Compute/virtualMachines", "vm-api-workers-prod"),
            "sku_name": "Standard_D8s_v3",
            "machine_family": "Dsv3",
            "playbook": "Aplicar resize em janela noturna com rollback preparado.\nValidar latencia por 24h.",
            "reason": "CPU e memoria abaixo do baseline de capacidade para picos normais.",
            "decision_evidence": {
                "cpu_p95": 18.4,
                "memory_p95": 42.7,
                "window_days": 30,
                "history_days": 90,
                "current_sku": "Standard_D8s_v3",
                "recommended_sku": "Standard_D4s_v3",
                "current_monthly_cost": 9100.0,
                "estimated_monthly_cost": 4900.0,
                "estimated_savings": 4200.0,
                "estimated_savings_pct": 46.2,
                "confidence": 0.87,
                "risk_level": "low",
                "reason": "CPU p95 e memoria p95 suportam downsizing com margem operacional.",
                "resource_type": "Microsoft.Compute/virtualMachines",
            },
        },
        {
            "title": "AKS nodepool rightsizing - pool user-prod",
            "description": "Nodepool user-prod no cluster aks-core-prod com sobrecapacidade media. Reduzir nodes e SKU.",
            "category": OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
            "risk_level": RiskLevel.MEDIUM,
            "effort_level": EffortLevel.MEDIUM,
            "monthly": 2800.0,
            "annual": 33600.0,
            "current": 5400.0,
            "score": 0.84,
            "status": OpportunityStatus.OPEN,
            "service": "Azure Kubernetes Service",
            "environment": "production",
            "owner_team": "platform",
            "resource_name": "aks-core-prod/user-prod",
            "resource_id": _make_resource_id("platform", "Microsoft.ContainerService/managedClusters", "aks-core-prod"),
            "sku_name": "Standard_D8s_v5",
            "machine_family": "Dsv5",
            "playbook": "Executar canary em 20% dos nodes.\nValidar pods pendentes e throttling.",
            "reason": "Uso sustentado do nodepool abaixo do limite economico.",
            "decision_evidence": {
                "cpu_p95": 31.2,
                "memory_p95": 54.1,
                "window_days": 30,
                "history_days": 90,
                "cluster_name": "aks-core-prod",
                "node_pool": "user-prod",
                "current_node_count": 12,
                "recommended_node_count": 8,
                "node_sku": "Standard_D8s_v5 -> Standard_D4s_v5",
                "allocated_cpu": 96.0,
                "allocated_memory": 384.0,
                "requested_cpu": 44.0,
                "requested_memory": 172.0,
                "has_kube_system_workloads": False,
                "has_critical_workloads": True,
                "confidence": 0.81,
                "risk_level": "medium",
                "reason": "Capacidade atual excede demanda p95 com folga acima de 2x.",
            },
        },
        {
            "title": "AKS autoscaler recommendation - pool user-prod",
            "description": "Habilitar/ajustar autoscaler no nodepool user-prod para reduzir desperdicio em horario ocioso.",
            "category": OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
            "risk_level": RiskLevel.LOW,
            "effort_level": EffortLevel.LOW,
            "monthly": 1600.0,
            "annual": 19200.0,
            "current": 5400.0,
            "score": 0.8,
            "status": OpportunityStatus.OPEN,
            "service": "Azure Kubernetes Service",
            "environment": "production",
            "owner_team": "platform",
            "resource_name": "aks-core-prod/user-prod",
            "resource_id": _make_resource_id("platform", "Microsoft.ContainerService/managedClusters", "aks-core-prod"),
            "sku_name": "Standard_D8s_v5",
            "machine_family": "Dsv5",
            "playbook": "Configurar min/max com SRE.\nMonitorar scaling events por 72h.",
            "reason": "Carga com alta variabilidade diaria e capacidade fixa superdimensionada.",
            "decision_evidence": {
                "cpu_p95": 38.3,
                "memory_p95": 57.4,
                "window_days": 30,
                "history_days": 90,
                "cluster_name": "aks-core-prod",
                "node_pool": "user-prod",
                "current_node_count": 12,
                "autoscaler_enabled": False,
                "autoscaler_action": "enable",
                "recommended_min_count": 5,
                "recommended_max_count": 14,
                "variability_score": 0.79,
                "cpu_p95_stddev": 12.2,
                "memory_p95_stddev": 10.4,
                "confidence": 0.78,
                "risk_level": "low",
                "reason": "Autoscaler reduz baseline mantendo headroom para bursts.",
            },
        },
        {
            "title": "Reserved Instances para VMs estaveis",
            "description": "Workloads com uptime alto e previsivel elegiveis para RI de 1 ano.",
            "category": OpportunityCategory.RESERVED_INSTANCES,
            "risk_level": RiskLevel.LOW,
            "effort_level": EffortLevel.LOW,
            "monthly": 5100.0,
            "annual": 61200.0,
            "current": 13800.0,
            "score": 0.85,
            "status": OpportunityStatus.OPEN,
            "service": "Virtual Machines",
            "environment": "production",
            "owner_team": "infra",
            "resource_name": "vm-stable-batch-prod",
            "resource_id": _make_resource_id("infra", "Microsoft.Compute/virtualMachines", "vm-stable-batch-prod"),
            "sku_name": "Standard_D8s_v3",
            "machine_family": "Dsv3",
            "playbook": "Comprar RI em lote piloto e revisar fatura no fechamento mensal.",
            "reason": "Padrao de uso constante sem sazonalidade relevante.",
            "decision_evidence": {"confidence": 0.83, "risk_level": "low", "reason": "Cobertura RI recomendada para carga constante."},
        },
        {
            "title": "Desligamento automatico de SQL dev/staging fora do expediente",
            "description": "Bancos de dev/staging ativos 24x7 podem ser pausados em janela noturna.",
            "category": OpportunityCategory.IDLE_RESOURCES,
            "risk_level": RiskLevel.LOW,
            "effort_level": EffortLevel.LOW,
            "monthly": 1800.0,
            "annual": 21600.0,
            "current": 3000.0,
            "score": 0.82,
            "status": OpportunityStatus.IN_PROGRESS,
            "service": "Azure SQL Database",
            "environment": "staging",
            "owner_team": "backend",
            "resource_name": "sql-dev-shared",
            "resource_id": _make_resource_id("backend", "Microsoft.Sql/servers/databases", "sql-dev-shared"),
            "sku_name": "GP_Gen5_8",
            "machine_family": "GeneralPurpose",
            "playbook": "Aplicar schedule 20h-08h em staging primeiro, depois dev.",
            "reason": "Baixa atividade fora de horario comercial.",
            "decision_evidence": {"confidence": 0.8, "risk_level": "low", "reason": "Uso noturno praticamente nulo."},
        },
        {
            "title": "Consolidacao de storage accounts legadas",
            "description": "Storage accounts com uso residual e baixo acesso podem ser consolidadas.",
            "category": OpportunityCategory.STORAGE_OPTIMIZATION,
            "risk_level": RiskLevel.LOW,
            "effort_level": EffortLevel.LOW,
            "monthly": 620.0,
            "annual": 7440.0,
            "current": 680.0,
            "score": 0.74,
            "status": OpportunityStatus.OPEN,
            "service": "Azure Storage",
            "environment": "production",
            "owner_team": "data",
            "resource_name": "st-legacy-archive",
            "resource_id": _make_resource_id("data", "Microsoft.Storage/storageAccounts", "st-legacy-archive"),
            "sku_name": "Standard_LRS",
            "machine_family": "Standard",
            "playbook": "Mover buckets menos acessados e validar regras de retencao.",
            "reason": "Baixo volume e baixa frequencia de acesso.",
            "decision_evidence": {"confidence": 0.74, "risk_level": "low", "reason": "Acesso historico baixo e previsivel."},
        },
        {
            "title": "Remover discos gerenciados nao anexados",
            "description": "Discos Premium SSD sem anexo ha mais de 30 dias podem ser removidos.",
            "category": OpportunityCategory.IDLE_RESOURCES,
            "risk_level": RiskLevel.LOW,
            "effort_level": EffortLevel.LOW,
            "monthly": 890.0,
            "annual": 10680.0,
            "current": 890.0,
            "score": 0.78,
            "status": OpportunityStatus.RESOLVED,
            "service": "Virtual Machines",
            "environment": "production",
            "owner_team": "infra",
            "resource_name": "disk-orphaned-group-a",
            "resource_id": _make_resource_id("infra", "Microsoft.Compute/disks", "disk-orphaned-group-a"),
            "sku_name": "Premium SSD",
            "machine_family": "Premium",
            "playbook": "Validar snapshots e remover por lote de 5 discos.",
            "reason": "Sem vinculo a VMs ativas.",
            "decision_evidence": {"confidence": 0.79, "risk_level": "low", "reason": "Recursos sem dependencia registrada."},
        },
    ]

    opp_ids = []
    for payload in OPPS:
        opp = OptimizationOpportunity(
            id=uuid.uuid4(),
            org_id=org_id,
            account_id=account_id,
            title=payload["title"],
            description=payload["description"],
            category=payload["category"],
            risk_level=payload["risk_level"],
            effort_level=payload["effort_level"],
            financial_impact_score=rng.uniform(0.5, 1.0),
            risk_score=rng.uniform(0.3, 1.0),
            effort_score=rng.uniform(0.2, 0.9),
            criticality_score=rng.uniform(0.4, 1.0),
            composite_score=payload["score"],
            estimated_monthly_savings_usd=float(payload["monthly"]),
            estimated_annual_savings_usd=float(payload["annual"]),
            current_monthly_cost_usd=float(payload["current"]),
            status=payload["status"],
            resource_id=payload["resource_id"],
            resource_name=payload["resource_name"],
            sku_name=payload["sku_name"],
            machine_family=payload["machine_family"],
            service=payload["service"],
            region="eastus",
            environment=payload["environment"],
            owner_team=payload["owner_team"],
            score_rationale=payload["reason"],
            playbook=payload["playbook"],
            decision_evidence=payload["decision_evidence"],
        )
        session.add(opp)
        opp_ids.append((opp.id, payload["title"]))

    await session.flush()
    print(f"  ✓ {len(OPPS)} opportunities demo criadas")

    # ── 3. Initiatives (workflow) ───────────────────────────────────────────
    INITIATIVES = [
        (opp_ids[0][0], "Right-size VM API workers - Sprint FinOps Q2", InitiativeStatus.IN_PROGRESS, 30, 4200),
        (opp_ids[1][0], "AKS nodepool tuning - canary rollout", InitiativeStatus.PLANNED, 14, 0),
        (opp_ids[2][0], "Enable AKS autoscaler in production", InitiativeStatus.IN_PROGRESS, 7, 0),
        (opp_ids[3][0], "Reserved Instances purchase wave 1", InitiativeStatus.PLANNED, 21, 0),
        (opp_ids[4][0], "Auto-shutdown SQL dev/staging", InitiativeStatus.DONE, None, 1800),
        (opp_ids[5][0], "Storage consolidation - legacy accounts", InitiativeStatus.BACKLOG, 45, 0),
        (opp_ids[6][0], "Cleanup orphaned managed disks", InitiativeStatus.DONE, None, 890),
    ]

    for opp_id, title, status, days_sla, savings in INITIATIVES:
        sla = (TODAY + timedelta(days=days_sla)) if days_sla else None
        completed = (datetime.now(timezone.utc) - timedelta(days=rng.randint(5, 30))) if status == InitiativeStatus.DONE else None
        init = Initiative(
            id=uuid.uuid4(),
            org_id=org_id,
            opportunity_id=opp_id,
            owner_id=user_id,
            title=title,
            status=status,
            sla_date=sla,
            completed_at=completed,
            realized_savings_usd=float(savings) if status == InitiativeStatus.DONE else None,
        )
        session.add(init)

    await session.flush()
    print(f"  ✓ {len(INITIATIVES)} initiatives criadas")

    # ── 4. Execution plan base para fluxo completo no frontend ──────────────
    from app.domains.intel.models import ExecutionPlan
    from app.domains.intel.schemas import CreateExecutionPlanRequest
    from app.domains.intel.execution_plan_service import ExecutionPlanService

    await session.execute(
        delete(ExecutionPlan).where(ExecutionPlan.org_id == org_id)
    )
    selected_for_plan = [oid for oid, _ in opp_ids[:3]]
    req = CreateExecutionPlanRequest(
        opportunity_ids=selected_for_plan,
        mode="manual_review",
    )
    plan = await ExecutionPlanService(session).prepare_plan(
        org_id=org_id,
        req=req,
        actor_user_id=user_id,
    )
    print(f"  ✓ execution_plan criado: {plan.execution_plan_id} ({plan.status})")

    await session.commit()
    return account_id


# ══════════════════════════════════════════════════════════════════════════════
# ClickHouse helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_resource_id(team: str, rtype: str, name: str) -> str:
    return (
        f"/subscriptions/{SUB_ID}/resourceGroups/rg-{team}"
        f"/providers/{rtype}/{name}"
    )


def seed_cost_facts(org_id: uuid.UUID, account_id: uuid.UUID) -> int:
    rows = []
    current = START_DATE
    while current <= TODAY:
        for service in SERVICES:
            team  = rng.choice(TEAMS)
            env   = rng.choice(ENVS)
            base  = rng.uniform(10, 1_200)
            if env == "production":
                base *= 2.8
            if current.weekday() >= 5:
                base *= 0.55
            if service == "Azure Kubernetes Service":
                base *= 3
            if service == "Azure SQL Database":
                base *= 2

            rows.append({
                "date": current,
                "org_id": str(org_id),
                "account_id": str(account_id),
                "provider": "azure",
                "subscription_id": SUB_ID,
                "service": service,
                "resource_id": _make_resource_id(team, RESOURCE_TYPES[0], f"{service.lower()[:8]}-{team}-01"),
                "resource_name": f"{service.lower()[:8]}-{team}",
                "region": rng.choice(REGIONS),
                "environment": env,
                "owner_team": team if rng.random() > 0.15 else "",   # 15% untagged
                "cost_usd": round(base, 4),
                "usage_quantity": round(rng.uniform(1, 500), 2),
                "usage_unit": "Units",
                "currency": "USD",
                "tags": {"team": team, "env": env},
            })
        current += timedelta(days=1)

    if not _insert_rows_safe("cost_facts", rows):
        return 0
    return len(rows)


def seed_event_facts(org_id: uuid.UUID, account_id: uuid.UUID) -> int:
    EVENT_TYPES = [
        ("Microsoft.Compute/virtualMachines/restart/action", "warning"),
        ("Microsoft.Sql/servers/databases/pause/action",     "informational"),
        ("Microsoft.Authorization/roleAssignments/write",    "warning"),
        ("Microsoft.Storage/storageAccounts/write",          "informational"),
        ("Microsoft.ContainerService/managedClusters/write", "informational"),
        ("Microsoft.Compute/virtualMachines/deallocate/action", "informational"),
        ("Microsoft.Security/alerts/write",                  "critical"),
        ("Microsoft.KeyVault/vaults/secrets/write",          "warning"),
    ]

    rows = []
    current = START_DATE
    while current <= TODAY:
        n = rng.randint(4, 20)
        for _ in range(n):
            etype, severity = rng.choice(EVENT_TYPES)
            team = rng.choice(TEAMS)
            ts   = datetime(
                current.year, current.month, current.day,
                rng.randint(0, 23), rng.randint(0, 59),
                tzinfo=timezone.utc,
            )
            rows.append({
                "timestamp": ts,
                "org_id": str(org_id),
                "account_id": str(account_id),
                "provider": "azure",
                "subscription_id": SUB_ID,
                "event_type": etype,
                "resource_id": _make_resource_id(team, RESOURCE_TYPES[0], f"vm-{team}-01"),
                "resource_name": f"vm-{team}-01",
                "region": rng.choice(REGIONS),
                "severity": severity,
                "description": f"Event: {etype.split('/')[-1]}",
                "caller": f"{team}-svc@nimbusops.io",
                "correlation_id": str(uuid.uuid4()),
                "raw_data": "{}",
            })
        current += timedelta(days=1)

    if not _insert_rows_safe("event_facts", rows):
        return 0
    return len(rows)


def seed_carbon_facts(org_id: uuid.UUID, account_id: uuid.UUID) -> int:
    rows = []
    month = date(START_DATE.year, START_DATE.month, 1)
    while month <= TODAY:
        ym = f"{month.year:04d}-{month.month:02d}"
        for service in SERVICES[:6]:
            rows.append({
                "year_month":      ym,
                "org_id":          str(org_id),
                "account_id":      str(account_id),
                "provider":        "azure",
                "subscription_id": SUB_ID,
                "service":         service,
                "resource_group":  f"rg-{rng.choice(TEAMS)}",
                "kg_co2e":         round(rng.uniform(20, 380), 3),
            })
        month = date(month.year + (month.month == 12), (month.month % 12) + 1, 1)

    if not _insert_rows_safe("carbon_facts", rows):
        return 0
    return len(rows)


def seed_recommendation_facts(org_id: uuid.UUID, account_id: uuid.UUID) -> int:
    now = datetime.now(timezone.utc)
    RECS = [
        ("Cost",     "High",   "Right-size or shut down underutilized virtual machines",         4_200.0),
        ("Cost",     "Medium", "Delete unattached managed disks",                                 890.0),
        ("Cost",     "Medium", "Purchase reserved instances for stable workloads (up to 37%%)",  5_100.0),
        ("Cost",     "Low",    "Remove unused public IP addresses",                                105.6),
        ("Security", "High",   "Enable Microsoft Defender for SQL servers",                       None),
        ("Security", "High",   "Rotate secrets older than 90 days in Key Vault",                  None),
        ("Security", "Medium", "Enable Microsoft Defender for Storage",                           None),
        ("Performance","Medium","Use Premium SSD for production database workloads",              None),
        ("HighAvailability","High","Configure Availability Zones for critical VMs",              None),
        ("OperationalExcellence","Low","Upgrade Azure SQL to latest supported version",          None),
    ]

    rows = []
    for i, (cat, impact, desc, savings) in enumerate(RECS):
        team = rng.choice(TEAMS)
        rg   = f"rg-{team}"
        name = f"vm-{team}-{i+1:02d}"
        rows.append({
            "fetched_at":             now,
            "org_id":                 str(org_id),
            "account_id":             str(account_id),
            "provider":               "azure",
            "subscription_id":        SUB_ID,
            "recommendation_id":      f"demo-rec-{i:04d}",
            "category":               cat,
            "impact":                 impact,
            "resource_id":            _make_resource_id(team, RESOURCE_TYPES[0], name),
            "resource_name":          name,
            "resource_group":         rg,
            "service":                "Microsoft.Compute/virtualMachines",
            "short_description":      desc,
            "recommendation_type_id": f"microsoft.advisor/demo/{i:04d}",
            "estimated_savings_usd":  savings,
        })

    if not _insert_rows_safe("recommendation_facts", rows):
        return 0
    return len(rows)


def seed_resource_inventory(org_id: uuid.UUID, account_id: uuid.UUID) -> int:
    now = datetime.now(timezone.utc)
    SKU_MAP = {
        "Microsoft.Compute/virtualMachines":          ("Standard_D4s_v3",  "Standard"),
        "Microsoft.Sql/servers/databases":            ("GeneralPurpose",   "GeneralPurpose"),
        "Microsoft.Storage/storageAccounts":          ("Standard_LRS",     "Standard"),
        "Microsoft.ContainerService/managedClusters": ("Standard",         "Paid"),
        "Microsoft.Web/sites":                        ("P2V2",             "PremiumV2"),
        "Microsoft.Cache/Redis":                      ("C1",               "Standard"),
        "Microsoft.KeyVault/vaults":                  ("",                 ""),
        "Microsoft.Network/virtualNetworks":          ("",                 ""),
    }

    rows = []
    for rtype, (sku_name, sku_tier) in SKU_MAP.items():
        count = rng.randint(3, 10)
        for i in range(count):
            team  = rng.choice(TEAMS)
            env   = rng.choice(ENVS)
            short = rtype.split("/")[-1].lower()[:12]
            name  = f"{short}-{team}-{i+1:02d}"
            rows.append({
                "fetched_at":         now,
                "org_id":             str(org_id),
                "account_id":         str(account_id),
                "provider":           "azure",
                "subscription_id":    SUB_ID,
                "resource_id":        _make_resource_id(team, rtype, name),
                "name":               name,
                "resource_type":      rtype,
                "resource_group":     f"rg-{team}-{env[:4]}",
                "location":           rng.choice(REGIONS),
                "environment":        env,
                "owner_team":         team if rng.random() > 0.1 else "untagged",
                "sku_name":           sku_name,
                "sku_tier":           sku_tier,
                "provisioning_state": "Succeeded",
                "tags":               {"team": team, "env": env},
            })

    if not _insert_rows_safe("resource_inventory", rows):
        return 0
    return len(rows)


def seed_usage_facts(org_id: uuid.UUID, account_id: uuid.UUID) -> int:
    METRICS = [
        ("Percentage CPU",    "Percent"),
        ("Network In Total",  "Bytes"),
        ("Network Out Total", "Bytes"),
    ]

    rows = []
    vms = [
        (_make_resource_id(team, RESOURCE_TYPES[0], f"vm-{team}-{i:02d}"), team, rng.choice(REGIONS))
        for team in TEAMS
        for i in range(1, 4)
    ]

    current = START_DATE
    while current <= TODAY:
        for vm_id, team, region in vms:
            for metric_name, unit in METRICS:
                if "CPU" in metric_name:
                    val = rng.uniform(8, 82)
                    if current.weekday() >= 5:
                        val *= 0.3
                else:
                    val = rng.uniform(500_000, 350_000_000)
                rows.append({
                    "date":            current,
                    "org_id":          str(org_id),
                    "account_id":      str(account_id),
                    "provider":        "azure",
                    "subscription_id": SUB_ID,
                    "service":         "Virtual Machines",
                    "resource_id":     vm_id,
                    "metric_name":     metric_name,
                    "metric_value":    round(val, 4),
                    "metric_unit":     unit,
                    "region":          region,
                    "environment":     rng.choice(ENVS),
                })
        current += timedelta(days=1)

    if not _insert_rows_safe("usage_facts", rows):
        return 0
    return len(rows)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    print("\n🌱  Iniciando seed de dados demo local...\n")

    engine  = make_engine()
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        print("── PostgreSQL ─────────────────────────────────────────")
        org_id, user_id = await ensure_demo_workspace(session)
        account_id = await seed_postgres(session, org_id=org_id, user_id=user_id)

    await engine.dispose()

    print("\n── ClickHouse ─────────────────────────────────────────")
    n = seed_cost_facts(org_id, account_id)
    print(f"  ✓ cost_facts:           {n:,} registros")

    n = seed_event_facts(org_id, account_id)
    print(f"  ✓ event_facts:          {n:,} registros")

    n = seed_carbon_facts(org_id, account_id)
    print(f"  ✓ carbon_facts:         {n:,} registros")

    n = seed_recommendation_facts(org_id, account_id)
    print(f"  ✓ recommendation_facts: {n:,} registros")

    n = seed_resource_inventory(org_id, account_id)
    print(f"  ✓ resource_inventory:   {n:,} registros")

    n = seed_usage_facts(org_id, account_id)
    print(f"  ✓ usage_facts:          {n:,} registros")

    print("\n✅  Seed concluido.")
    print(f"   Workspace: {DEMO_ORG_NAME}")
    print(f"   Login:     {DEMO_USER_EMAIL}")
    print(f"   Senha:     {DEMO_USER_PASSWORD}")
    print("   Abra o frontend local para validar o fluxo completo.\n")


if __name__ == "__main__":
    asyncio.run(main())
