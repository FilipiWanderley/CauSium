"""Mock Azure connector — returns realistic synthetic data when credentials are absent."""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from app.core.logging import get_logger
from app.domains.connectors.base import BaseConnector, CanonicalCostRecord, CanonicalEventRecord

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


def _make_resource_id(subscription_id: str, service: str, team: str) -> str:
    rg = f"rg-{team}"
    resource_type = service.lower().replace(" ", "-")[:20]
    return f"/subscriptions/{subscription_id}/resourceGroups/{rg}/providers/Microsoft.Mock/{resource_type}/r-{random.randint(1000, 9999)}"


class AzureMockClient(BaseConnector):
    """Deterministic mock — seed based on subscription_id for reproducibility."""

    async def validate_connection(self) -> None:
        log.info("azure.mock.validate_connection.ok")

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
                        tags={"team": team, "env": env, "managed-by": "stratopulse"},
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
