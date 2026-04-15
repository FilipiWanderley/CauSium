"""Mock Azure connector — returns realistic synthetic data when credentials are absent."""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from app.core.logging import get_logger
from app.domains.connectors.base import (
    BaseConnector,
    CanonicalCarbonRecord,
    CanonicalCostRecord,
    CanonicalEventRecord,
    CanonicalRecommendationRecord,
    CanonicalResourceRecord,
    CanonicalUsageRecord,
)

log = get_logger(__name__)

SERVICES = [
    "Virtual Machines", "Azure Kubernetes Service", "Azure SQL Database",
    "Azure Storage", "Azure Functions", "App Service", "Azure Cache for Redis",
    "Azure Monitor", "Azure Active Directory", "Bandwidth",
]
REGIONS = ["eastus", "westeurope", "brazilsouth", "eastus2", "southeastasia"]
ENVIRONMENTS = ["production", "staging", "development"]
TEAMS = ["platform", "backend", "data", "frontend", "security", "infra"]
EVENT_TYPES = [
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/deallocate/action",
    "Microsoft.Sql/servers/databases/pause/action",
    "Microsoft.Storage/storageAccounts/write",
    "Microsoft.ContainerService/managedClusters/write",
    "Microsoft.Authorization/roleAssignments/write",
]
SEVERITIES = ["informational", "warning", "error", "critical"]

# Resource types used for mock inventory
_RESOURCE_TYPES: list[tuple[str, str, str]] = [
    ("Microsoft.Compute/virtualMachines",          "Standard_D4s_v3",   "Standard"),
    ("Microsoft.Sql/servers/databases",            "GeneralPurpose",    "GeneralPurpose"),
    ("Microsoft.Storage/storageAccounts",          "Standard_LRS",      "Standard"),
    ("Microsoft.ContainerService/managedClusters", "Standard",          "Paid"),
    ("Microsoft.Web/sites",                        "P2V2",              "PremiumV2"),
    ("Microsoft.Cache/Redis",                      "C1",                "Standard"),
    ("Microsoft.KeyVault/vaults",                  "",                  ""),
    ("Microsoft.Network/virtualNetworks",          "",                  ""),
]

# Advisor recommendation templates (category, impact, description, annual_savings_usd | None)
_MOCK_ADVISOR_RECS: list[tuple[str, str, str, str, float | None]] = [
    ("Cost",                  "High",   "Right-size or shut down underutilized virtual machines",                       "microsoft.advisor/rightsizing",        1_250.00),
    ("Cost",                  "Medium", "Delete unattached managed disks to reduce costs",                              "microsoft.advisor/idledisk",             480.00),
    ("Cost",                  "Medium", "Purchase reserved capacity for consistent workloads to save up to 72%%",       "microsoft.advisor/reservedinstances",  3_200.00),
    ("Cost",                  "Low",    "Remove unused public IP addresses",                                            "microsoft.advisor/unusedpublicip",        87.60),
    ("Security",              "High",   "Enable Microsoft Defender for SQL servers on machines",                        "microsoft.advisor/defenderSQL",            None),
    ("Security",              "Medium", "Enable Microsoft Defender for Storage accounts",                               "microsoft.advisor/defenderStorage",        None),
    ("Performance",           "Medium", "Use Premium SSD managed disks for production virtual machine workloads",       "microsoft.advisor/premiumssd",             None),
    ("HighAvailability",      "High",   "Configure availability zones for your critical virtual machines",              "microsoft.advisor/availabilityzones",      None),
    ("OperationalExcellence", "Low",    "Upgrade your Azure SQL Database to the latest available version",              "microsoft.advisor/sqlversion",             None),
]


def _make_resource_id(subscription_id: str, service: str, team: str) -> str:
    rg = f"rg-{team}"
    resource_type = service.lower().replace(" ", "-")[:20]
    return f"/subscriptions/{subscription_id}/resourceGroups/{rg}/providers/Microsoft.Mock/{resource_type}/r-{random.randint(1000, 9999)}"


class AzureMockClient(BaseConnector):
    """Deterministic mock — seed based on subscription_id for reproducibility."""

    async def validate_connection(self) -> None:
        log.info("azure.mock.validate_connection.ok")

    async def validate_cost_management_scope(self, subscription_id: str) -> None:
        log.info("azure.mock.scope_validation.ok", subscription_id=subscription_id)

    async def fetch_costs(
        self, subscription_id: str, start: date, end: date
    ) -> list[CanonicalCostRecord]:
        rng = random.Random(subscription_id + str(start))
        records: list[CanonicalCostRecord] = []
        current = start

        while current <= end:
            for service in SERVICES:
                team = rng.choice(TEAMS)
                env = rng.choice(ENVIRONMENTS)
                base_cost = rng.uniform(5, 800)
                # Simulate weekend dip
                if current.weekday() >= 5:
                    base_cost *= 0.6
                # Prod costs more
                if env == "production":
                    base_cost *= 2.5

                records.append(
                    CanonicalCostRecord(
                        date=current,
                        provider="azure",
                        subscription_id=subscription_id,
                        service=service,
                        resource_id=_make_resource_id(subscription_id, service, team),
                        resource_name=f"{team}-{service.lower().replace(' ', '-')[:15]}",
                        region=rng.choice(REGIONS),
                        environment=env,
                        owner_team=team,
                        cost_usd=round(base_cost, 4),
                        usage_quantity=round(rng.uniform(1, 1000), 2),
                        usage_unit="Units",
                        currency="USD",
                        tags={"team": team, "env": env, "managed-by": "causium"},
                    )
                )
            current += timedelta(days=1)

        log.info("azure.mock.fetch_costs.done", subscription=subscription_id, records=len(records))
        return records

    async def fetch_events(
        self, subscription_id: str, start: date, end: date
    ) -> list[CanonicalEventRecord]:
        rng = random.Random(subscription_id + "events" + str(start))
        records: list[CanonicalEventRecord] = []
        current = start

        while current <= end:
            n_events = rng.randint(3, 15)
            for _ in range(n_events):
                team = rng.choice(TEAMS)
                event_type = rng.choice(EVENT_TYPES)
                hour = rng.randint(0, 23)
                minute = rng.randint(0, 59)
                ts = datetime(current.year, current.month, current.day, hour, minute, tzinfo=timezone.utc)

                records.append(
                    CanonicalEventRecord(
                        timestamp=ts,
                        provider="azure",
                        subscription_id=subscription_id,
                        event_type=event_type,
                        resource_id=_make_resource_id(subscription_id, "Virtual Machines", team),
                        resource_name=f"vm-{team}-{rng.randint(1, 9)}",
                        region=rng.choice(REGIONS),
                        severity=rng.choice(SEVERITIES),
                        description=f"Mock event: {event_type.split('/')[-1]}",
                        caller=f"user-{team}@company.com",
                        correlation_id=f"mock-{rng.randint(100000, 999999)}",
                        raw_data="{}",
                    )
                )
            current += timedelta(days=1)

        log.info("azure.mock.fetch_events.done", subscription=subscription_id, records=len(records))
        return records

    async def fetch_carbon_emissions(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCarbonRecord]:
        rng = random.Random(subscription_id + "carbon" + str(start))
        records: list[CanonicalCarbonRecord] = []

        month = date(start.year, start.month, 1)
        last_month = date(end.year, end.month, 1)

        while month <= last_month:
            for service in SERVICES[:5]:
                records.append(
                    CanonicalCarbonRecord(
                        year_month=f"{month.year:04d}-{month.month:02d}",
                        provider="azure",
                        subscription_id=subscription_id,
                        service=service,
                        resource_group=f"rg-{rng.choice(TEAMS)}",
                        kg_co2e=round(rng.uniform(10, 250), 3),
                    )
                )

            if month.month == 12:
                month = date(month.year + 1, 1, 1)
            else:
                month = date(month.year, month.month + 1, 1)

        log.info("azure.mock.fetch_carbon.done", subscription=subscription_id, records=len(records))
        return records

    async def fetch_recommendations(
        self, subscription_id: str
    ) -> list[CanonicalRecommendationRecord]:
        rng = random.Random(subscription_id + "recommendations")
        now = datetime.now(timezone.utc)
        records: list[CanonicalRecommendationRecord] = []

        for i, (category, impact, description, rec_type_id, savings) in enumerate(_MOCK_ADVISOR_RECS):
            team = rng.choice(TEAMS)
            rg = f"rg-{team}"
            vm_name = f"vm-{team}-{rng.randint(1, 9):02d}"
            resource_id = (
                f"/subscriptions/{subscription_id}/resourceGroups/{rg}"
                f"/providers/Microsoft.Compute/virtualMachines/{vm_name}"
            )
            records.append(
                CanonicalRecommendationRecord(
                    recommendation_id=f"mock-{abs(hash(subscription_id + description)) % 10 ** 8:08d}",
                    provider="azure",
                    subscription_id=subscription_id,
                    category=category,
                    impact=impact,
                    resource_id=resource_id,
                    resource_name=vm_name,
                    resource_group=rg,
                    service="Microsoft.Compute/virtualMachines",
                    short_description=description,
                    recommendation_type_id=rec_type_id,
                    estimated_savings_usd=savings,
                    fetched_at=now,
                )
            )

        log.info("azure.mock.fetch_recommendations.done", subscription=subscription_id, records=len(records))
        return records

    async def fetch_inventory(
        self, subscription_id: str
    ) -> list[CanonicalResourceRecord]:
        rng = random.Random(subscription_id + "inventory")
        now = datetime.now(timezone.utc)
        records: list[CanonicalResourceRecord] = []

        for resource_type, sku_name, sku_tier in _RESOURCE_TYPES:
            count = rng.randint(2, 8)
            for i in range(count):
                team = rng.choice(TEAMS)
                env = rng.choice(ENVIRONMENTS)
                rg = f"rg-{team}-{env[:4]}"
                short_type = resource_type.split("/")[-1].lower()[:12]
                name = f"{short_type}-{team}-{i + 1:02d}"
                resource_id = (
                    f"/subscriptions/{subscription_id}/resourceGroups/{rg}"
                    f"/providers/{resource_type}/{name}"
                )
                tags = {"team": team, "env": env, "managed-by": "nimbusops"}
                records.append(
                    CanonicalResourceRecord(
                        resource_id=resource_id,
                        provider="azure",
                        subscription_id=subscription_id,
                        name=name,
                        resource_type=resource_type,
                        resource_group=rg,
                        location=rng.choice(REGIONS),
                        environment=env,
                        owner_team=team,
                        sku_name=sku_name,
                        sku_tier=sku_tier,
                        provisioning_state="Succeeded",
                        tags=tags,
                        fetched_at=now,
                    )
                )

        log.info("azure.mock.fetch_inventory.done", subscription=subscription_id, records=len(records))
        return records

    async def fetch_usage_metrics(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalUsageRecord]:
        rng = random.Random(subscription_id + "usage" + str(start))
        records: list[CanonicalUsageRecord] = []

        VM_METRICS: list[tuple[str, str]] = [
            ("Percentage CPU",   "Percent"),
            ("Network In Total", "Bytes"),
            ("Network Out Total","Bytes"),
        ]

        # Simulate a handful of VMs across teams
        vms = [
            (
                f"/subscriptions/{subscription_id}/resourceGroups/rg-{team}"
                f"/providers/Microsoft.Compute/virtualMachines/vm-{team}-{i:02d}",
                team,
                rng.choice(REGIONS),
                rng.choice(ENVIRONMENTS),
            )
            for team in TEAMS[:3]
            for i in range(1, 4)
        ]

        current = start
        while current <= end:
            for vm_id, _team, region, environment in vms:
                for metric_name, metric_unit in VM_METRICS:
                    if "CPU" in metric_name:
                        # Weekend dip; prod is busier
                        base = rng.uniform(8.0, 75.0)
                        if current.weekday() >= 5:
                            base *= 0.35
                    elif "In" in metric_name:
                        base = rng.uniform(1_000_000, 400_000_000)
                    else:
                        base = rng.uniform(500_000, 150_000_000)

                    records.append(
                        CanonicalUsageRecord(
                            date=current,
                            provider="azure",
                            subscription_id=subscription_id,
                            service="Virtual Machines",
                            resource_id=vm_id,
                            metric_name=metric_name,
                            metric_value=round(base, 4),
                            metric_unit=metric_unit,
                            region=region,
                            environment=environment,
                        )
                    )
            current += timedelta(days=1)

        log.info("azure.mock.fetch_usage.done", subscription=subscription_id, records=len(records))
        return records
