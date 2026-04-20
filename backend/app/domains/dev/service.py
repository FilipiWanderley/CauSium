from __future__ import annotations
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_command, insert_rows
from app.core.logging import get_logger
from app.domains.cloud_accounts.models import CloudAccount, CloudProvider, ConnectorStatus
from app.domains.dev.schemas import ClearResult, SeedRequest, SeedResult

log = get_logger(__name__)

# Marker that identifies programmatically-created mock accounts so we can
# target them safely in clear operations without touching real accounts.
_MOCK_EXTERNAL_ID_PREFIX = "mock-seed-"

# ---------------------------------------------------------------------------
# Static data tables used during generation
# ---------------------------------------------------------------------------

_AZURE_ACCOUNT_EXTERNAL_ID = f"{_MOCK_EXTERNAL_ID_PREFIX}azure-sub-001"
_AWS_ACCOUNT_EXTERNAL_ID = f"{_MOCK_EXTERNAL_ID_PREFIX}aws-123456789012"
_GCP_ACCOUNT_EXTERNAL_ID = f"{_MOCK_EXTERNAL_ID_PREFIX}gcp-project-001"

_AZURE_SUBSCRIPTION_ID = "aaaaaaaa-0000-0000-0000-aaaaaaaaaaaa"
_AWS_ACCOUNT_NUMBER = "123456789012"
_GCP_PROJECT_ID = "causium-mock-001"

_AZURE_SERVICES: list[dict[str, Any]] = [
    {"service": "Virtual Machines",  "resource_type": "Microsoft.Compute/virtualMachines", "region": "eastus",      "environment": "production", "team": "platform", "sku": "Standard_D4s_v3", "base_cost": 48.0,  "unit": "hours", "qty": 24.0},
    {"service": "Azure Kubernetes Service", "resource_type": "Microsoft.ContainerService/managedClusters", "region": "eastus", "environment": "production", "team": "platform", "sku": "Standard", "base_cost": 32.0, "unit": "hours", "qty": 24.0},
    {"service": "Azure SQL Database",  "resource_type": "Microsoft.Sql/servers/databases", "region": "eastus",      "environment": "production", "team": "data",     "sku": "GP_Gen5_4", "base_cost": 18.0,  "unit": "DTUs",  "qty": 100.0},
    {"service": "Storage",             "resource_type": "Microsoft.Storage/storageAccounts", "region": "eastus",   "environment": "production", "team": "data",     "sku": "Standard_LRS", "base_cost": 10.0, "unit": "GB",    "qty": 512.0},
    {"service": "App Service",         "resource_type": "Microsoft.Web/sites", "region": "brazilsouth", "environment": "staging",    "team": "backend",  "sku": "P1v3", "base_cost": 14.0,  "unit": "hours", "qty": 24.0},
    {"service": "Azure Functions",     "resource_type": "Microsoft.Web/sites", "region": "westus2",     "environment": "development","team": "backend",  "sku": "Consumption", "base_cost": 4.0, "unit": "executions", "qty": 50000.0},
]

_AWS_SERVICES: list[dict[str, Any]] = [
    {"service": "Amazon EC2",       "resource_type": "AWS::EC2::Instance",       "region": "us-east-1", "environment": "production", "team": "platform", "sku": "m5.xlarge",  "base_cost": 40.0, "unit": "hours",   "qty": 24.0},
    {"service": "Amazon RDS",       "resource_type": "AWS::RDS::DBInstance",      "region": "us-east-1", "environment": "production", "team": "data",     "sku": "db.r5.large","base_cost": 25.0, "unit": "hours",   "qty": 24.0},
    {"service": "Amazon S3",        "resource_type": "AWS::S3::Bucket",           "region": "us-east-1", "environment": "production", "team": "data",     "sku": "Standard",   "base_cost": 8.0,  "unit": "GB",      "qty": 800.0},
    {"service": "AWS Lambda",       "resource_type": "AWS::Lambda::Function",     "region": "us-east-1", "environment": "production", "team": "backend",  "sku": "ARM",        "base_cost": 3.5,  "unit": "requests","qty": 1_000_000.0},
    {"service": "Amazon CloudFront","resource_type": "AWS::CloudFront::Distribution","region": "us-east-1","environment": "production","team": "infra",   "sku": "Standard",   "base_cost": 11.0, "unit": "GB",      "qty": 300.0},
]

_GCP_SERVICES: list[dict[str, Any]] = [
    {"service": "Compute Engine", "resource_type": "compute.googleapis.com/Instance",      "region": "us-central1", "environment": "production", "team": "platform",  "sku": "n2-standard-4", "base_cost": 30.0, "unit": "hours", "qty": 24.0},
    {"service": "Cloud SQL",      "resource_type": "sqladmin.googleapis.com/Instance",     "region": "us-central1", "environment": "production", "team": "data",      "sku": "db-n1-standard-2","base_cost": 15.0,"unit": "hours", "qty": 24.0},
    {"service": "Cloud Storage",  "resource_type": "storage.googleapis.com/Bucket",        "region": "us-central1", "environment": "production", "team": "data",      "sku": "Standard",      "base_cost": 6.0,  "unit": "GB",    "qty": 400.0},
    {"service": "BigQuery",       "resource_type": "bigquery.googleapis.com/Dataset",      "region": "us-central1", "environment": "production", "team": "analytics", "sku": "On-demand",     "base_cost": 20.0, "unit": "TB",    "qty": 0.5},
]

_EVENT_TYPES = [
    ("Deploy",          "low",      "Successful deployment of application version"),
    ("ScalingEvent",    "low",      "Auto-scale triggered: capacity adjusted"),
    ("ConfigChange",    "medium",   "Configuration updated in production environment"),
    ("CertRotation",    "low",      "TLS certificate rotated successfully"),
    ("IncidentDetected","high",     "Anomalous cost spike detected by monitoring"),
    ("PolicyViolation", "medium",   "Resource tag policy violation detected"),
    ("BackupCompleted", "low",      "Scheduled backup completed successfully"),
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DevSeedService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def is_seeded(self, org_id: UUID) -> bool:
        result = await self.db.execute(
            select(CloudAccount).where(
                CloudAccount.org_id == org_id,
                CloudAccount.external_id.like(f"{_MOCK_EXTERNAL_ID_PREFIX}%"),
            )
        )
        return result.scalar_one_or_none() is not None

    async def seed(self, org_id: UUID, req: SeedRequest) -> SeedResult:
        if await self.is_seeded(org_id):
            if not req.force:
                raise ValueError(
                    "Tenant already has seed data. Use force=true to overwrite."
                )
            await self.clear(org_id)

        accounts = await self._create_mock_accounts(org_id)
        await self.db.flush()

        # Deterministic RNG seeded from org_id so the same tenant always
        # gets the same shape of data across service restarts.
        rng = random.Random(int.from_bytes(org_id.bytes, "big"))

        azure_acct, aws_acct, gcp_acct = accounts
        today = date.today()

        cost_rows = self._gen_cost_facts(org_id, azure_acct, aws_acct, gcp_acct, today, req.days, rng)
        event_rows = self._gen_event_facts(org_id, azure_acct, aws_acct, gcp_acct, today, rng)
        usage_rows = self._gen_usage_facts(org_id, azure_acct, aws_acct, gcp_acct, today, req.days, rng)
        rec_rows = self._gen_recommendation_facts(org_id, azure_acct, aws_acct, gcp_acct, rng)
        inv_rows = self._gen_resource_inventory(org_id, azure_acct, aws_acct, gcp_acct, rng)

        insert_rows("cost_facts", cost_rows)
        insert_rows("event_facts", event_rows)
        insert_rows("usage_facts", usage_rows)
        insert_rows("recommendation_facts", rec_rows)
        insert_rows("resource_inventory", inv_rows)

        await self.db.commit()

        log.info(
            "dev_seed.completed",
            org_id=str(org_id),
            cost_records=len(cost_rows),
            event_records=len(event_rows),
            usage_records=len(usage_rows),
            days=req.days,
        )

        return SeedResult(
            org_id=org_id,
            accounts_created=len(accounts),
            cost_records=len(cost_rows),
            event_records=len(event_rows),
            usage_records=len(usage_rows),
            recommendation_records=len(rec_rows),
            resource_records=len(inv_rows),
            days_seeded=req.days,
        )

    async def clear(self, org_id: UUID) -> ClearResult:
        # Remove mock CloudAccounts from PostgreSQL.
        await self.db.execute(
            sa_delete(CloudAccount).where(
                CloudAccount.org_id == org_id,
                CloudAccount.external_id.like(f"{_MOCK_EXTERNAL_ID_PREFIX}%"),
            )
        )

        # Lightweight delete from every ClickHouse analytical table.
        # org_id is a Python UUID — no user input, safe to interpolate.
        org_str = str(org_id)
        for table in (
            "cost_facts",
            "event_facts",
            "usage_facts",
            "recommendation_facts",
            "resource_inventory",
        ):
            execute_command(f"DELETE FROM {table} WHERE org_id = '{org_str}'")

        await self.db.commit()

        log.info("dev_seed.cleared", org_id=org_str)
        return ClearResult(org_id=org_id, cleared=True)

    # ------------------------------------------------------------------
    # Account creation
    # ------------------------------------------------------------------

    async def _create_mock_accounts(self, org_id: UUID) -> tuple[CloudAccount, CloudAccount, CloudAccount]:
        now = datetime.now(timezone.utc)

        azure = CloudAccount(
            org_id=org_id,
            provider=CloudProvider.AZURE,
            external_id=_AZURE_ACCOUNT_EXTERNAL_ID,
            display_name="Azure Production (Mock)",
            tenant_id="mock-tenant-id",
            status=ConnectorStatus.ACTIVE,
            last_sync_at=now,
        )
        aws = CloudAccount(
            org_id=org_id,
            provider=CloudProvider.AWS,
            external_id=_AWS_ACCOUNT_EXTERNAL_ID,
            display_name="AWS Production (Mock)",
            status=ConnectorStatus.ACTIVE,
            last_sync_at=now,
        )
        gcp = CloudAccount(
            org_id=org_id,
            provider=CloudProvider.GCP,
            external_id=_GCP_ACCOUNT_EXTERNAL_ID,
            display_name="GCP Production (Mock)",
            status=ConnectorStatus.ACTIVE,
            last_sync_at=now,
        )
        self.db.add_all([azure, aws, gcp])
        await self.db.flush()
        await self.db.refresh(azure)
        await self.db.refresh(aws)
        await self.db.refresh(gcp)
        return azure, aws, gcp

    # ------------------------------------------------------------------
    # Cost facts — daily rows per service for every requested day
    # ------------------------------------------------------------------

    def _gen_cost_facts(
        self,
        org_id: UUID,
        azure: CloudAccount,
        aws: CloudAccount,
        gcp: CloudAccount,
        today: date,
        days: int,
        rng: random.Random,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        provider_matrix = [
            (azure, "azure",  _AZURE_SUBSCRIPTION_ID, _AZURE_SERVICES),
            (aws,   "aws",    _AWS_ACCOUNT_NUMBER,     _AWS_SERVICES),
            (gcp,   "gcp",    _GCP_PROJECT_ID,         _GCP_SERVICES),
        ]

        for day_offset in range(days):
            day = today - timedelta(days=day_offset)
            # Simulate a weekend dip (~20 % lower costs on Sat/Sun).
            weekend_factor = 0.80 if day.weekday() >= 5 else 1.0

            for account, provider, subscription_id, services in provider_matrix:
                for svc in services:
                    variance = rng.uniform(0.88, 1.12)
                    cost = round(svc["base_cost"] * weekend_factor * variance, 4)
                    qty = round(svc["qty"] * weekend_factor * rng.uniform(0.9, 1.1), 2)

                    rows.append({
                        "date": day,
                        "org_id": org_id,
                        "account_id": account.id,
                        "provider": provider,
                        "subscription_id": subscription_id,
                        "service": svc["service"],
                        "resource_id": f"/{provider}/{subscription_id}/{svc['resource_type']}/mock-{svc['service'].lower().replace(' ', '-')}-01",
                        "resource_name": f"mock-{svc['service'].lower().replace(' ', '-')}-01",
                        "region": svc["region"],
                        "environment": svc["environment"],
                        "owner_team": svc["team"],
                        "cost_usd": cost,
                        "usage_quantity": qty,
                        "usage_unit": svc["unit"],
                        "currency": "USD",
                        "tags": {"environment": svc["environment"], "team": svc["team"]},
                    })

        return rows

    # ------------------------------------------------------------------
    # Event facts — change events spread over last 30 days
    # ------------------------------------------------------------------

    def _gen_event_facts(
        self,
        org_id: UUID,
        azure: CloudAccount,
        aws: CloudAccount,
        gcp: CloudAccount,
        today: date,
        rng: random.Random,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        provider_accounts = [
            (azure, "azure", _AZURE_SUBSCRIPTION_ID),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER),
            (gcp,   "gcp",   _GCP_PROJECT_ID),
        ]

        for day_offset in range(30):
            day = today - timedelta(days=day_offset)
            events_today = rng.randint(1, 4)

            for _ in range(events_today):
                account, provider, subscription_id = rng.choice(provider_accounts)
                event_type, severity, description = rng.choice(_EVENT_TYPES)
                hour = rng.randint(0, 23)
                minute = rng.randint(0, 59)

                rows.append({
                    "timestamp": datetime(day.year, day.month, day.day, hour, minute, 0, tzinfo=timezone.utc),
                    "org_id": org_id,
                    "account_id": account.id,
                    "provider": provider,
                    "subscription_id": subscription_id,
                    "event_type": event_type,
                    "resource_id": f"/{provider}/mock-resource-{rng.randint(1, 5):02d}",
                    "resource_name": f"mock-resource-{rng.randint(1, 5):02d}",
                    "region": rng.choice(["eastus", "us-east-1", "us-central1"]),
                    "severity": severity,
                    "description": description,
                    "caller": f"mock-service-principal@{provider}.com",
                    "correlation_id": str(uuid4()),
                    "raw_data": "{}",
                })

        return rows

    # ------------------------------------------------------------------
    # Usage facts — daily resource utilisation metrics
    # ------------------------------------------------------------------

    def _gen_usage_facts(
        self,
        org_id: UUID,
        azure: CloudAccount,
        aws: CloudAccount,
        gcp: CloudAccount,
        today: date,
        days: int,
        rng: random.Random,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        metrics = [
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Virtual Machines",  "eastus",      "cpu_percent",    65.0,  "%"),
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Virtual Machines",  "eastus",      "memory_percent", 72.0,  "%"),
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Storage",           "eastus",      "storage_used_gb",512.0, "GB"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "Amazon EC2",        "us-east-1",   "cpu_percent",    55.0,  "%"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "Amazon RDS",        "us-east-1",   "connections",    45.0,  "count"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "Amazon S3",         "us-east-1",   "storage_used_gb",800.0, "GB"),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "Compute Engine",    "us-central1", "cpu_percent",    60.0,  "%"),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "BigQuery",          "us-central1", "bytes_processed",0.5,   "TB"),
        ]

        for day_offset in range(days):
            day = today - timedelta(days=day_offset)
            for account, provider, subscription_id, service, region, metric_name, base_value, unit in metrics:
                value = round(base_value * rng.uniform(0.80, 1.15), 2)
                rows.append({
                    "date": day,
                    "org_id": org_id,
                    "account_id": account.id,
                    "provider": provider,
                    "subscription_id": subscription_id,
                    "service": service,
                    "resource_id": f"/{provider}/mock-{service.lower().replace(' ', '-')}-01",
                    "metric_name": metric_name,
                    "metric_value": value,
                    "metric_unit": unit,
                    "region": region,
                    "environment": "production",
                })

        return rows

    # ------------------------------------------------------------------
    # Recommendation facts — cost-saving opportunities
    # ------------------------------------------------------------------

    def _gen_recommendation_facts(
        self,
        org_id: UUID,
        azure: CloudAccount,
        aws: CloudAccount,
        gcp: CloudAccount,
        rng: random.Random,
    ) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)

        recommendations = [
            # (account, provider, subscription_id, category, impact, service, description, savings_usd)
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Cost",         "High",   "Virtual Machines",       "Right-size underutilised VM from D4s_v3 to D2s_v3",        320.0),
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Cost",         "Medium", "Azure Kubernetes Service","Switch AKS node pool to spot instances for non-prod",       180.0),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "Cost",         "High",   "Amazon EC2",             "Purchase 1-year reserved instances for steady-state EC2",   450.0),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "Cost",         "Medium", "Amazon RDS",             "Enable RDS storage auto-scaling to avoid over-provisioning", 120.0),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "Cost",         "High",   "Compute Engine",         "Commit to 1-year CUDs for Compute Engine baseline",          280.0),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "Performance",  "Medium", "BigQuery",               "Partition billing export table to reduce scanned bytes",       60.0),
        ]

        rows: list[dict[str, Any]] = []
        for account, provider, subscription_id, category, impact, service, description, savings in recommendations:
            rows.append({
                "fetched_at": now,
                "org_id": org_id,
                "account_id": account.id,
                "provider": provider,
                "subscription_id": subscription_id,
                "recommendation_id": str(uuid4()),
                "category": category,
                "impact": impact,
                "resource_id": f"/{provider}/mock-{service.lower().replace(' ', '-')}-01",
                "resource_name": f"mock-{service.lower().replace(' ', '-')}-01",
                "resource_group": "mock-rg-production" if provider == "azure" else "",
                "service": service,
                "short_description": description,
                "recommendation_type_id": f"mock-type-{provider}-{rng.randint(100, 999)}",
                "estimated_savings_usd": savings,
            })

        return rows

    # ------------------------------------------------------------------
    # Resource inventory — current state of provisioned resources
    # ------------------------------------------------------------------

    def _gen_resource_inventory(
        self,
        org_id: UUID,
        azure: CloudAccount,
        aws: CloudAccount,
        gcp: CloudAccount,
        rng: random.Random,
    ) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)

        resources = [
            # (account, provider, subscription_id, resource_type, name, resource_group, location, env, team, sku_name, sku_tier)
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.Compute/virtualMachines",       "vm-prod-app-01",      "mock-rg-production", "eastus",      "production", "platform",  "Standard_D4s_v3",   "Standard"),
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.ContainerService/managedClusters","aks-prod-cluster-01","mock-rg-production", "eastus",      "production", "platform",  "Standard",          "Standard"),
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.Sql/servers/databases",          "sqldb-prod-main-01",  "mock-rg-production", "eastus",      "production", "data",      "GP_Gen5_4",         "GeneralPurpose"),
            (azure, "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.Storage/storageAccounts",        "stprodcausium01",     "mock-rg-production", "eastus",      "production", "data",      "Standard_LRS",      "Standard"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::EC2::Instance",                        "ec2-prod-app-01",     "",                   "us-east-1",   "production", "platform",  "m5.xlarge",         "On-Demand"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::RDS::DBInstance",                      "rds-prod-postgres-01","",                   "us-east-1",   "production", "data",      "db.r5.large",       "Standard"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::S3::Bucket",                           "causium-prod-data-01","",                   "us-east-1",   "production", "data",      "Standard",          "Standard"),
            (aws,   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::Lambda::Function",                     "lambda-prod-api-01",  "",                   "us-east-1",   "production", "backend",   "ARM",               "Serverless"),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "compute.googleapis.com/Instance",           "vm-prod-app-01",      "",                   "us-central1", "production", "platform",  "n2-standard-4",     "Standard"),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "sqladmin.googleapis.com/Instance",          "sql-prod-postgres-01","",                   "us-central1", "production", "data",      "db-n1-standard-2",  "Standard"),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "storage.googleapis.com/Bucket",             "causium-prod-data-01","",                   "us-central1", "production", "data",      "Standard",          "Standard"),
            (gcp,   "gcp",   _GCP_PROJECT_ID,        "bigquery.googleapis.com/Dataset",           "causium_analytics_01","",                   "us-central1", "production", "analytics", "On-demand",         "Standard"),
        ]

        rows: list[dict[str, Any]] = []
        for account, provider, subscription_id, resource_type, name, resource_group, location, env, team, sku_name, sku_tier in resources:
            rows.append({
                "fetched_at": now,
                "org_id": org_id,
                "account_id": account.id,
                "provider": provider,
                "subscription_id": subscription_id,
                "resource_id": f"/{provider}/{subscription_id}/{resource_type}/{name}",
                "name": name,
                "resource_type": resource_type,
                "resource_group": resource_group,
                "location": location,
                "environment": env,
                "owner_team": team,
                "sku_name": sku_name,
                "sku_tier": sku_tier,
                "provisioning_state": "Succeeded",
                "tags": {"environment": env, "team": team},
            })

        return rows
