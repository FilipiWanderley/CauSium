"""
seed_demo.py — Popula dados fictícios realistas para apresentação.

Execução:
    docker exec -it stratopulse-backend-1 python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# ── paths ──────────────────────────────────────────────────────────────────────
sys.path.insert(0, "/app")

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.clickhouse import insert_rows
from app.core.config import get_settings

settings = get_settings()
rng = random.Random(42)

# ── constants ──────────────────────────────────────────────────────────────────

ORG_ID   = uuid.UUID("429cfe60-1d95-413e-ad7e-bccb4a76af3b")
USER_ID  = uuid.UUID("73cbbca3-1c75-4959-ab88-e37ef37839ee")

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


# ══════════════════════════════════════════════════════════════════════════════
# PostgreSQL helpers
# ══════════════════════════════════════════════════════════════════════════════

def make_engine():
    return create_async_engine(settings.database_url, echo=False)


async def seed_postgres(session: AsyncSession) -> uuid.UUID:
    import app.domains.admin.models  # noqa: F401 — registers Organization in mapper
    from app.domains.cloud_accounts.models import CloudAccount, CloudProvider, ConnectorStatus
    from app.domains.decision_engine.models import (
        EffortLevel, OpportunityCategory, OptimizationOpportunity,
        RiskLevel, OpportunityStatus,
    )
    from app.domains.workflow.models import Initiative, InitiativeStatus

    # ── 1. Cloud account ────────────────────────────────────────────────────
    existing = await session.execute(
        select(CloudAccount).where(CloudAccount.org_id == ORG_ID)
    )
    account = existing.scalars().first()

    if not account:
        account = CloudAccount(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            provider=CloudProvider.AZURE,
            external_id=SUB_ID,
            display_name="NimbusOps — Azure Production",
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

    # ── 2. Optimization opportunities ──────────────────────────────────────
    existing_opps = await session.execute(
        select(OptimizationOpportunity).where(OptimizationOpportunity.org_id == ORG_ID)
    )
    if existing_opps.scalars().first():
        print("  · opportunities já existem, pulando")
        return account_id

    OPPS = [
        ("Right-size VMs subutilizadas no cluster AKS",
         "Instâncias D8s_v3 com CPU médio < 12%. Migrar para D4s_v3 reduz custo em 45%.",
         OpportunityCategory.RIGHTSIZING, RiskLevel.LOW, EffortLevel.LOW,
         4_200, 50_400, 9_100, 0.87),
        ("Desligar bancos SQL de desenvolvimento fora do horário comercial",
         "11 bancos de dev/staging ativos 24h. Schedule stop 20h–8h reduz 60% do custo.",
         OpportunityCategory.IDLE_RESOURCES, RiskLevel.LOW, EffortLevel.LOW,
         1_800, 21_600, 3_000, 0.82),
        ("Migrar workloads batch para Spot VMs",
         "Jobs de processamento de dados rodam em VMs on-demand. Spot reduz até 80%.",
         OpportunityCategory.RIGHTSIZING, RiskLevel.MEDIUM, EffortLevel.MEDIUM,
         3_100, 37_200, 3_900, 0.79),
        ("Consolidar 6 Storage Accounts subutilizadas",
         "Accounts com < 10 GB e sem acesso há 60+ dias. Consolidar libera $ e reduz surface de ataque.",
         OpportunityCategory.STORAGE_OPTIMIZATION, RiskLevel.LOW, EffortLevel.LOW,
         620, 7_440, 680, 0.74),
        ("Habilitar Azure Defender for SQL em todos os servidores",
         "3 servidores SQL sem Defender ativo. Risco de exposição a SQL injection e exfiltração.",
         OpportunityCategory.ARCHITECTURE_CHANGE, RiskLevel.HIGH, EffortLevel.LOW,
         0, 0, 0, 0.91),
        ("Rotacionar segredos com mais de 90 dias no Key Vault",
         "14 segredos sem rotação há > 90 dias. Política de segurança exige rotação trimestral.",
         OpportunityCategory.LICENSE_OPTIMIZATION, RiskLevel.HIGH, EffortLevel.LOW,
         0, 0, 0, 0.88),
        ("Configurar Availability Zones para VMs de produção críticas",
         "8 VMs de produção em zona única. SLA 99.9% → 99.99% com multi-AZ.",
         OpportunityCategory.ARCHITECTURE_CHANGE, RiskLevel.HIGH, EffortLevel.HIGH,
         0, 0, 12_000, 0.76),
        ("Implementar auto-scaling no AKS para workloads variáveis",
         "Cluster AKS com node count fixo. Horizontal Pod Autoscaler reduz desperdício em horários off-peak.",
         OpportunityCategory.RIGHTSIZING, RiskLevel.LOW, EffortLevel.MEDIUM,
         2_400, 28_800, 1_200, 0.71),
        ("Atualizar imagens de container com vulnerabilidades críticas (CVE-2024-*)",
         "Scan do ACR identificou 6 imagens com CVEs críticos. Atualização necessária.",
         OpportunityCategory.ARCHITECTURE_CHANGE, RiskLevel.HIGH, EffortLevel.MEDIUM,
         0, 0, 0, 0.93),
        ("Reserved Instances para VMs de produção estáveis",
         "12 VMs com uptime > 95% nos últimos 6 meses. Reserva 1 ano = economia de 37%.",
         OpportunityCategory.RESERVED_INSTANCES, RiskLevel.LOW, EffortLevel.LOW,
         5_100, 61_200, 13_800, 0.85),
        ("Remover discos gerenciados não anexados",
         "23 discos Premium SSD sem VM associada há > 30 dias. Custo recorrente sem uso.",
         OpportunityCategory.IDLE_RESOURCES, RiskLevel.LOW, EffortLevel.LOW,
         890, 10_680, 890, 0.78),
        ("Migrar logs de diagnóstico para Storage cool tier",
         "Logs retidos em hot tier por 180 dias. Cool tier reduz custo de storage em 65%.",
         OpportunityCategory.STORAGE_OPTIMIZATION, RiskLevel.LOW, EffortLevel.LOW,
         340, 4_080, 340, 0.65),
    ]

    statuses = [
        OpportunityStatus.OPEN, OpportunityStatus.OPEN, OpportunityStatus.OPEN,
        OpportunityStatus.IN_PROGRESS, OpportunityStatus.IN_PROGRESS,
        OpportunityStatus.OPEN, OpportunityStatus.OPEN, OpportunityStatus.IN_PROGRESS,
        OpportunityStatus.OPEN, OpportunityStatus.OPEN,
        OpportunityStatus.RESOLVED, OpportunityStatus.RESOLVED,
    ]

    opp_ids = []
    for i, (title, desc, cat, risk, effort, monthly, annual, current, score) in enumerate(OPPS):
        opp = OptimizationOpportunity(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            account_id=account_id,
            title=title,
            description=desc,
            category=cat,
            risk_level=risk,
            effort_level=effort,
            financial_impact_score=rng.uniform(0.5, 1.0),
            risk_score=rng.uniform(0.3, 1.0),
            effort_score=rng.uniform(0.2, 0.9),
            criticality_score=rng.uniform(0.4, 1.0),
            composite_score=score,
            estimated_monthly_savings_usd=float(monthly),
            estimated_annual_savings_usd=float(annual),
            current_monthly_cost_usd=float(current),
            status=statuses[i],
        )
        session.add(opp)
        opp_ids.append((opp.id, title))

    await session.flush()
    print(f"  ✓ {len(OPPS)} opportunities criadas")

    # ── 3. Initiatives (workflow) ───────────────────────────────────────────
    INITIATIVES = [
        (opp_ids[0][0],  "Right-size AKS nodes — Sprint FinOps Q2",   InitiativeStatus.IN_PROGRESS, 30, 4_200),
        (opp_ids[1][0],  "Auto-shutdown dev/staging DBs",              InitiativeStatus.DONE,        None, 1_800),
        (opp_ids[3][0],  "Consolidação de Storage Accounts legadas",   InitiativeStatus.PLANNED,     14, 0),
        (opp_ids[4][0],  "Ativar Defender for SQL — todos os envs",    InitiativeStatus.IN_PROGRESS, 7,  0),
        (opp_ids[5][0],  "Rotação de segredos Key Vault — Q2",         InitiativeStatus.BACKLOG,     45, 0),
        (opp_ids[9][0],  "Reserved Instances — VMs produção estáveis", InitiativeStatus.PLANNED,     21, 0),
        (opp_ids[10][0], "Limpeza de discos órfãos — fev/2026",        InitiativeStatus.DONE,        None, 890),
    ]

    for opp_id, title, status, days_sla, savings in INITIATIVES:
        sla = (TODAY + timedelta(days=days_sla)) if days_sla else None
        completed = (datetime.now(timezone.utc) - timedelta(days=rng.randint(5, 30))) if status == InitiativeStatus.DONE else None
        init = Initiative(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            opportunity_id=opp_id,
            owner_id=USER_ID,
            title=title,
            status=status,
            sla_date=sla,
            completed_at=completed,
            realized_savings_usd=float(savings) if status == InitiativeStatus.DONE else None,
        )
        session.add(init)

    await session.flush()
    print(f"  ✓ {len(INITIATIVES)} initiatives criadas")

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

    insert_rows("cost_facts", rows)
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

    insert_rows("event_facts", rows)
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

    insert_rows("carbon_facts", rows)
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

    insert_rows("recommendation_facts", rows)
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

    insert_rows("resource_inventory", rows)
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

    insert_rows("usage_facts", rows)
    return len(rows)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    print("\n🌱  Iniciando seed de dados demo...\n")

    engine  = make_engine()
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        print("── PostgreSQL ─────────────────────────────────────────")
        account_id = await seed_postgres(session)

    await engine.dispose()

    print("\n── ClickHouse ─────────────────────────────────────────")
    n = seed_cost_facts(ORG_ID, account_id)
    print(f"  ✓ cost_facts:           {n:,} registros")

    n = seed_event_facts(ORG_ID, account_id)
    print(f"  ✓ event_facts:          {n:,} registros")

    n = seed_carbon_facts(ORG_ID, account_id)
    print(f"  ✓ carbon_facts:         {n:,} registros")

    n = seed_recommendation_facts(ORG_ID, account_id)
    print(f"  ✓ recommendation_facts: {n:,} registros")

    n = seed_resource_inventory(ORG_ID, account_id)
    print(f"  ✓ resource_inventory:   {n:,} registros")

    n = seed_usage_facts(ORG_ID, account_id)
    print(f"  ✓ usage_facts:          {n:,} registros")

    print("\n✅  Seed concluído. Abre o dashboard em http://localhost:3000\n")


if __name__ == "__main__":
    asyncio.run(main())
