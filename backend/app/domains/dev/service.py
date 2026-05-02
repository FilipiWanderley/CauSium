from __future__ import annotations
import json
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_command, execute_query, insert_rows
from app.core.logging import get_logger
from app.domains.cloud_accounts.models import CloudAccount, CloudProvider, ConnectorStatus
from app.domains.dev.schemas import ClearResult, SeedRequest, SeedResult, SeedStatus
from app.domains.economics.models import FinancialBudgetPeriod, WorkspaceBudget
from app.domains.risk_budgets.models import BudgetPeriod, BudgetType, RiskBudget
from app.domains.experiments.models import ExperimentStatus, OptimizationExperiment
from app.domains.intel.models import CostAnomaly, CostAnomalySeverity
from app.domains.decision_engine.models import (
    EffortLevel, OpportunityCategory, OpportunityStatus, OptimizationOpportunity, RiskLevel,
)

log = get_logger(__name__)

# Marker that identifies programmatically-created mock accounts so we can
# target them safely in clear operations without touching real accounts.
_MOCK_EXTERNAL_ID_PREFIX = "mock-seed-"

# ---------------------------------------------------------------------------
# Static data tables used during generation
# ---------------------------------------------------------------------------

_AZURE_ACCOUNT_EXTERNAL_ID = f"{_MOCK_EXTERNAL_ID_PREFIX}azure-sub-001"
_AWS_ACCOUNT_EXTERNAL_ID   = f"{_MOCK_EXTERNAL_ID_PREFIX}aws-123456789012"
_GCP_ACCOUNT_EXTERNAL_ID   = f"{_MOCK_EXTERNAL_ID_PREFIX}gcp-project-001"

_AZURE_SUBSCRIPTION_ID = "aaaaaaaa-0000-0000-0000-aaaaaaaaaaaa"
_AWS_ACCOUNT_NUMBER    = "123456789012"
_GCP_PROJECT_ID        = "causium-mock-001"

_AZURE_SERVICES: list[dict[str, Any]] = [
    {"service": "Virtual Machines",         "resource_type": "Microsoft.Compute/virtualMachines",           "region": "eastus",      "environment": "production",  "team": "platform",  "sku": "Standard_D4s_v3",    "base_cost": 48.0,  "unit": "hours",      "qty": 24.0},
    {"service": "Azure Kubernetes Service", "resource_type": "Microsoft.ContainerService/managedClusters", "region": "eastus",      "environment": "production",  "team": "platform",  "sku": "Standard",            "base_cost": 32.0,  "unit": "hours",      "qty": 24.0},
    {"service": "Azure SQL Database",       "resource_type": "Microsoft.Sql/servers/databases",            "region": "eastus",      "environment": "production",  "team": "data",      "sku": "GP_Gen5_4",           "base_cost": 18.0,  "unit": "DTUs",       "qty": 100.0},
    {"service": "Storage",                  "resource_type": "Microsoft.Storage/storageAccounts",          "region": "eastus",      "environment": "production",  "team": "data",      "sku": "Standard_LRS",        "base_cost": 10.0,  "unit": "GB",         "qty": 512.0},
    {"service": "App Service",              "resource_type": "Microsoft.Web/sites",                        "region": "brazilsouth", "environment": "staging",     "team": "backend",   "sku": "P1v3",                "base_cost": 14.0,  "unit": "hours",      "qty": 24.0},
    {"service": "Azure Functions",          "resource_type": "Microsoft.Web/sites",                        "region": "westus2",     "environment": "development", "team": "backend",   "sku": "Consumption",         "base_cost": 4.0,   "unit": "executions", "qty": 50000.0},
]

_AWS_SERVICES: list[dict[str, Any]] = [
    {"service": "Amazon EC2",        "resource_type": "AWS::EC2::Instance",            "region": "us-east-1", "environment": "production", "team": "platform", "sku": "m5.xlarge",   "base_cost": 40.0, "unit": "hours",    "qty": 24.0},
    {"service": "Amazon RDS",        "resource_type": "AWS::RDS::DBInstance",          "region": "us-east-1", "environment": "production", "team": "data",     "sku": "db.r5.large", "base_cost": 25.0, "unit": "hours",    "qty": 24.0},
    {"service": "Amazon S3",         "resource_type": "AWS::S3::Bucket",               "region": "us-east-1", "environment": "production", "team": "data",     "sku": "Standard",    "base_cost": 8.0,  "unit": "GB",       "qty": 800.0},
    {"service": "AWS Lambda",        "resource_type": "AWS::Lambda::Function",         "region": "us-east-1", "environment": "production", "team": "backend",  "sku": "ARM",         "base_cost": 3.5,  "unit": "requests", "qty": 1_000_000.0},
    {"service": "Amazon CloudFront", "resource_type": "AWS::CloudFront::Distribution", "region": "us-east-1", "environment": "production", "team": "infra",    "sku": "Standard",    "base_cost": 11.0, "unit": "GB",       "qty": 300.0},
]

_GCP_SERVICES: list[dict[str, Any]] = [
    {"service": "Compute Engine", "resource_type": "compute.googleapis.com/Instance",  "region": "us-central1", "environment": "production", "team": "platform",  "sku": "n2-standard-4",   "base_cost": 30.0, "unit": "hours", "qty": 24.0},
    {"service": "Cloud SQL",      "resource_type": "sqladmin.googleapis.com/Instance", "region": "us-central1", "environment": "production", "team": "data",      "sku": "db-n1-standard-2", "base_cost": 15.0, "unit": "hours", "qty": 24.0},
    {"service": "Cloud Storage",  "resource_type": "storage.googleapis.com/Bucket",    "region": "us-central1", "environment": "production", "team": "data",      "sku": "Standard",         "base_cost": 6.0,  "unit": "GB",    "qty": 400.0},
    {"service": "BigQuery",       "resource_type": "bigquery.googleapis.com/Dataset",  "region": "us-central1", "environment": "production", "team": "analytics", "sku": "On-demand",        "base_cost": 20.0, "unit": "TB",    "qty": 0.5},
]

_EVENT_TYPES = [
    ("Deploy",           "low",    "Successful deployment of application version"),
    ("ScalingEvent",     "low",    "Auto-scale triggered: capacity adjusted"),
    ("ConfigChange",     "medium", "Configuration updated in production environment"),
    ("CertRotation",     "low",    "TLS certificate rotated successfully"),
    ("IncidentDetected", "high",   "Anomalous cost spike detected by monitoring"),
    ("PolicyViolation",  "medium", "Resource tag policy violation detected"),
    ("BackupCompleted",  "low",    "Scheduled backup completed successfully"),
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
        return result.scalars().first() is not None

    async def status(self, org_id: UUID) -> SeedStatus:
        """Return row counts from ClickHouse for the tenant — useful for diagnostics."""
        org_str = str(org_id)

        def _count(table: str) -> int:
            try:
                rows = execute_query(
                    f"SELECT count() AS cnt FROM {table} WHERE org_id = {{org_id:String}}",
                    {"org_id": org_str},
                )
                return int(rows[0]["cnt"]) if rows else 0
            except Exception as exc:
                log.warning("dev_seed.status.count_failed", table=table, error=str(exc))
                return -1

        return SeedStatus(
            org_id=org_id,
            seeded=await self.is_seeded(org_id),
            cost_records=_count("cost_facts"),
            event_records=_count("event_facts"),
            usage_records=_count("usage_facts"),
            recommendation_records=_count("recommendation_facts"),
            resource_records=_count("resource_inventory"),
        )

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

        # ClickHouse tables
        cost_rows  = self._gen_cost_facts(org_id, azure_acct, aws_acct, gcp_acct, today, req.days, rng)
        event_rows = self._gen_event_facts(org_id, azure_acct, aws_acct, gcp_acct, today, rng)
        usage_rows = self._gen_usage_facts(org_id, azure_acct, aws_acct, gcp_acct, today, req.days, rng)
        rec_rows   = self._gen_recommendation_facts(org_id, azure_acct, aws_acct, gcp_acct, rng)
        inv_rows   = self._gen_resource_inventory(org_id, azure_acct, aws_acct, gcp_acct, rng)

        self._insert_table("cost_facts",           cost_rows)
        self._insert_table("event_facts",          event_rows)
        self._insert_table("usage_facts",          usage_rows)
        self._insert_table("recommendation_facts", rec_rows)
        self._insert_table("resource_inventory",   inv_rows)

        # PostgreSQL records
        await self._create_workspace_budget(org_id, cost_rows, req.days)
        risk_budgets = await self._create_risk_budgets(org_id)
        experiments  = await self._create_experiments(org_id, rng)
        anomalies    = await self._create_cost_anomalies(org_id, cost_rows, rng)
        opportunities = await self._create_opportunities(org_id, accounts, rng)

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
        # PostgreSQL — remove all seed-generated records
        await self.db.execute(
            sa_delete(CloudAccount).where(
                CloudAccount.org_id == org_id,
                CloudAccount.external_id.like(f"{_MOCK_EXTERNAL_ID_PREFIX}%"),
            )
        )
        await self.db.execute(sa_delete(WorkspaceBudget).where(WorkspaceBudget.org_id == org_id))
        await self.db.execute(sa_delete(RiskBudget).where(RiskBudget.org_id == org_id))
        await self.db.execute(sa_delete(OptimizationExperiment).where(OptimizationExperiment.org_id == org_id))
        await self.db.execute(sa_delete(CostAnomaly).where(CostAnomaly.org_id == org_id))
        await self.db.execute(sa_delete(OptimizationOpportunity).where(OptimizationOpportunity.org_id == org_id))

        # ClickHouse — delete from every analytical table
        org_str = str(org_id)
        for table in (
            "cost_facts",
            "event_facts",
            "usage_facts",
            "recommendation_facts",
            "resource_inventory",
        ):
            try:
                execute_command(f"DELETE FROM {table} WHERE org_id = '{org_str}'")
            except Exception as exc:
                log.warning("dev_seed.clear.delete_failed", table=table, error=str(exc))

        await self.db.commit()

        log.info("dev_seed.cleared", org_id=org_str)
        return ClearResult(org_id=org_id, cleared=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _insert_table(table: str, rows: list[dict[str, Any]]) -> None:
        """Wrap insert_rows with per-table error logging so failures are visible."""
        try:
            insert_rows(table, rows)
            log.info("dev_seed.insert_ok", table=table, rows=len(rows))
        except Exception as exc:
            log.error("dev_seed.insert_failed", table=table, error=str(exc))
            raise RuntimeError(f"ClickHouse insert failed for '{table}': {exc}") from exc

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
        # ⚠️  org_id and account_id MUST be strings — the ClickHouse queries
        #     use {org_id:String} parameters, which require string values.
        org_str   = str(org_id)
        azure_str = str(azure.id)
        aws_str   = str(aws.id)
        gcp_str   = str(gcp.id)

        rows: list[dict[str, Any]] = []

        provider_matrix = [
            (azure_str, "azure", _AZURE_SUBSCRIPTION_ID, _AZURE_SERVICES),
            (aws_str,   "aws",   _AWS_ACCOUNT_NUMBER,    _AWS_SERVICES),
            (gcp_str,   "gcp",   _GCP_PROJECT_ID,        _GCP_SERVICES),
        ]

        for day_offset in range(days):
            day = today - timedelta(days=day_offset)
            # Simulate a weekend dip (~20 % lower costs on Sat/Sun).
            weekend_factor = 0.80 if day.weekday() >= 5 else 1.0

            for account_str, provider, subscription_id, services in provider_matrix:
                for svc in services:
                    variance = rng.uniform(0.88, 1.12)
                    cost = round(svc["base_cost"] * weekend_factor * variance, 4)
                    qty  = round(svc["qty"] * weekend_factor * rng.uniform(0.9, 1.1), 2)

                    rows.append({
                        "date":           day,
                        "org_id":         org_str,
                        "account_id":     account_str,
                        "provider":       provider,
                        "subscription_id": subscription_id,
                        "service":        svc["service"],
                        "resource_id":    f"/{provider}/{subscription_id}/{svc['resource_type']}/mock-{svc['service'].lower().replace(' ', '-')}-01",
                        "resource_name":  f"mock-{svc['service'].lower().replace(' ', '-')}-01",
                        "region":         svc["region"],
                        "environment":    svc["environment"],
                        "owner_team":     svc["team"],
                        "cost_usd":       cost,
                        "usage_quantity": qty,
                        "usage_unit":     svc["unit"],
                        "currency":       "USD",
                        "tags":           json.dumps({"environment": svc["environment"], "team": svc["team"]}),
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
        org_str = str(org_id)

        provider_accounts = [
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID),
        ]

        rows: list[dict[str, Any]] = []

        for day_offset in range(30):
            day = today - timedelta(days=day_offset)
            events_today = rng.randint(1, 4)

            for _ in range(events_today):
                account_str, provider, subscription_id = rng.choice(provider_accounts)
                event_type, severity, description = rng.choice(_EVENT_TYPES)
                hour   = rng.randint(0, 23)
                minute = rng.randint(0, 59)

                rows.append({
                    "timestamp":      datetime(day.year, day.month, day.day, hour, minute, 0),
                    "org_id":         org_str,
                    "account_id":     account_str,
                    "provider":       provider,
                    "subscription_id": subscription_id,
                    "event_type":     event_type,
                    "resource_id":    f"/{provider}/mock-resource-{rng.randint(1, 5):02d}",
                    "resource_name":  f"mock-resource-{rng.randint(1, 5):02d}",
                    "region":         rng.choice(["eastus", "us-east-1", "us-central1"]),
                    "severity":       severity,
                    "description":    description,
                    "caller":         f"mock-service-principal@{provider}.com",
                    "correlation_id": str(uuid4()),
                    "raw_data":       "{}",
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
        org_str = str(org_id)

        metrics = [
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Virtual Machines", "eastus",      "cpu_percent",    65.0,  "%"),
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Virtual Machines", "eastus",      "memory_percent", 72.0,  "%"),
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Storage",          "eastus",      "storage_used_gb",512.0, "GB"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "Amazon EC2",       "us-east-1",   "cpu_percent",    55.0,  "%"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "Amazon RDS",       "us-east-1",   "connections",    45.0,  "count"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "Amazon S3",        "us-east-1",   "storage_used_gb",800.0, "GB"),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "Compute Engine",   "us-central1", "cpu_percent",    60.0,  "%"),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "BigQuery",         "us-central1", "bytes_processed",0.5,   "TB"),
        ]

        rows: list[dict[str, Any]] = []

        for day_offset in range(days):
            day = today - timedelta(days=day_offset)
            for account_str, provider, subscription_id, service, region, metric_name, base_value, unit in metrics:
                value = round(base_value * rng.uniform(0.80, 1.15), 2)
                rows.append({
                    "date":           day,
                    "org_id":         org_str,
                    "account_id":     account_str,
                    "provider":       provider,
                    "subscription_id": subscription_id,
                    "service":        service,
                    "resource_id":    f"/{provider}/mock-{service.lower().replace(' ', '-')}-01",
                    "metric_name":    metric_name,
                    "metric_value":   value,
                    "metric_unit":    unit,
                    "region":         region,
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
        org_str = str(org_id)

        recommendations = [
            # (account_str, provider, subscription_id, category, impact, service, description, savings_usd)
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Cost",        "High",   "Virtual Machines",       "Right-size underutilised VM from D4s_v3 to D2s_v3",         320.0),
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Cost",        "Medium", "Azure Kubernetes Service","Switch AKS node pool to spot instances for non-prod",        180.0),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "Cost",        "High",   "Amazon EC2",             "Purchase 1-year reserved instances for steady-state EC2",    450.0),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "Cost",        "Medium", "Amazon RDS",             "Enable RDS storage auto-scaling to avoid over-provisioning",  120.0),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "Cost",        "High",   "Compute Engine",         "Commit to 1-year CUDs for Compute Engine baseline",           280.0),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "Performance", "Medium", "BigQuery",               "Partition billing export table to reduce scanned bytes",        60.0),
        ]

        rows: list[dict[str, Any]] = []
        today = date.today()
        for account_str, provider, subscription_id, category, impact, service, description, savings in recommendations:
            rows.append({
                "date":                   today,
                "org_id":                 org_str,
                "account_id":             account_str,
                "provider":               provider,
                "subscription_id":        subscription_id,
                "category":               category,
                "impact":                 impact,
                "resource_id":            f"/{provider}/mock-{service.lower().replace(' ', '-')}-01",
                "resource_name":          f"mock-{service.lower().replace(' ', '-')}-01",
                "service":                service,
                "short_description":      description,
                "recommendation_type_id": f"mock-type-{provider}-{rng.randint(100, 999)}",
                "resource_type":          f"mock/{service.lower().replace(' ', '-')}",
                "sku_name":               "",
                "sku_tier":               "",
                "estimated_savings_usd":  savings,
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
        org_str = str(org_id)
        now = datetime.now(timezone.utc)

        resources = [
            # (account_str, provider, subscription_id, resource_type, name, resource_group, location, env, team, sku_name, sku_tier)
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.Compute/virtualMachines",          "vm-prod-app-01",       "mock-rg-production", "eastus",      "production", "platform",  "Standard_D4s_v3",    "Standard"),
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.ContainerService/managedClusters", "aks-prod-cluster-01",  "mock-rg-production", "eastus",      "production", "platform",  "Standard",           "Standard"),
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.Sql/servers/databases",            "sqldb-prod-main-01",   "mock-rg-production", "eastus",      "production", "data",      "GP_Gen5_4",          "GeneralPurpose"),
            (str(azure.id), "azure", _AZURE_SUBSCRIPTION_ID, "Microsoft.Storage/storageAccounts",          "stprodcausium01",      "mock-rg-production", "eastus",      "production", "data",      "Standard_LRS",       "Standard"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::EC2::Instance",                          "ec2-prod-app-01",      "",                   "us-east-1",   "production", "platform",  "m5.xlarge",          "On-Demand"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::RDS::DBInstance",                        "rds-prod-postgres-01", "",                   "us-east-1",   "production", "data",      "db.r5.large",        "Standard"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::S3::Bucket",                             "causium-prod-data-01", "",                   "us-east-1",   "production", "data",      "Standard",           "Standard"),
            (str(aws.id),   "aws",   _AWS_ACCOUNT_NUMBER,    "AWS::Lambda::Function",                       "lambda-prod-api-01",   "",                   "us-east-1",   "production", "backend",   "ARM",                "Serverless"),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "compute.googleapis.com/Instance",             "vm-prod-app-01",       "",                   "us-central1", "production", "platform",  "n2-standard-4",      "Standard"),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "sqladmin.googleapis.com/Instance",            "sql-prod-postgres-01", "",                   "us-central1", "production", "data",      "db-n1-standard-2",   "Standard"),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "storage.googleapis.com/Bucket",               "causium-prod-data-01", "",                   "us-central1", "production", "data",      "Standard",           "Standard"),
            (str(gcp.id),   "gcp",   _GCP_PROJECT_ID,        "bigquery.googleapis.com/Dataset",             "causium_analytics_01", "",                   "us-central1", "production", "analytics", "On-demand",          "Standard"),
        ]

        rows: list[dict[str, Any]] = []
        for account_str, provider, subscription_id, resource_type, name, resource_group, location, env, team, sku_name, sku_tier in resources:
            rows.append({
                "fetched_at":        now,
                "org_id":            org_str,
                "account_id":        account_str,
                "provider":          provider,
                "subscription_id":   subscription_id,
                "resource_id":       f"/{provider}/{subscription_id}/{resource_type}/{name}",
                "name":              name,
                "resource_type":     resource_type,
                "resource_group":    resource_group,
                "location":          location,
                "environment":       env,
                "owner_team":        team,
                "sku_name":          sku_name,
                "sku_tier":          sku_tier,
                "provisioning_state": "Succeeded",
                "tags":              json.dumps({"environment": env, "team": team}),
            })

        return rows

    # ------------------------------------------------------------------
    # PostgreSQL — WorkspaceBudget
    # ------------------------------------------------------------------

    async def _create_workspace_budget(
        self, org_id: UUID, cost_rows: list[dict[str, Any]], days: int
    ) -> WorkspaceBudget:
        # Estimate monthly spend from cost_rows to set a realistic budget
        total_cost = sum(float(r.get("cost_usd") or 0) for r in cost_rows)
        avg_daily  = total_cost / max(days, 1)
        monthly_estimate = avg_daily * 30

        # Budget = 110% of average monthly spend (slightly above to show partial consumption)
        budget_amount = round(monthly_estimate * 1.10, 2)

        budget = WorkspaceBudget(
            org_id=org_id,
            amount_usd=budget_amount,
            period=FinancialBudgetPeriod.MONTHLY,
            currency="USD",
            alert_thresholds="[50, 80, 90]",
        )
        self.db.add(budget)
        await self.db.flush()
        log.info("dev_seed.budget_created", org_id=str(org_id), amount_usd=budget_amount)
        return budget

    # ------------------------------------------------------------------
    # PostgreSQL — RiskBudgets
    # ------------------------------------------------------------------

    async def _create_risk_budgets(self, org_id: UUID) -> list[RiskBudget]:
        configs = [
            ("Platform Cost Variance — Production",  "platform",  "production",  BudgetType.COST_VARIANCE,    BudgetPeriod.WEEKLY,   15.0),
            ("Data Team Cost Variance — Production",  "data",      "production",  BudgetType.COST_VARIANCE,    BudgetPeriod.WEEKLY,   20.0),
            ("Backend Blast Radius — Staging",        "backend",   "staging",     BudgetType.BLAST_RADIUS,     BudgetPeriod.DAILY,    0.25),
            ("Platform Change Frequency — Production","platform",  "production",  BudgetType.CHANGE_FREQUENCY, BudgetPeriod.WEEKLY,   10.0),
            ("Infra Error Rate — Production",         "infra",     "production",  BudgetType.ERROR_RATE,       BudgetPeriod.DAILY,    0.05),
        ]
        budgets: list[RiskBudget] = []
        for name, domain, env, btype, period, limit in configs:
            rb = RiskBudget(
                org_id=org_id,
                name=name,
                domain=domain,
                environment=env,
                budget_type=btype,
                period=period,
                limit_value=limit,
                current_value=round(limit * 0.6, 4),
                is_active=True,
            )
            self.db.add(rb)
            budgets.append(rb)
        await self.db.flush()
        log.info("dev_seed.risk_budgets_created", org_id=str(org_id), count=len(budgets))
        return budgets

    # ------------------------------------------------------------------
    # PostgreSQL — OptimizationExperiments
    # ------------------------------------------------------------------

    async def _create_experiments(
        self, org_id: UUID, rng: random.Random
    ) -> list[OptimizationExperiment]:
        specs = [
            (
                "Right-size Standard_D4s_v3 VMs to Standard_D2s_v3",
                "Downsizing underutilized VMs (avg CPU < 30%) will reduce compute costs by ~40% with no performance impact.",
                "production", "medium",
                ExperimentStatus.APPROVED,
                1200.0, 0.82,
            ),
            (
                "Enable Reserved Instances for Azure SQL Database",
                "Switching from pay-as-you-go to 1-year reserved capacity for stable workloads saves ~35%.",
                "production", "low",
                ExperimentStatus.RUNNING,
                650.0, 0.91,
            ),
            (
                "Migrate Azure Functions to Consumption plan",
                "Low-traffic functions on Premium plan can move to Consumption to eliminate idle costs.",
                "staging", "low",
                ExperimentStatus.CONCLUDED,
                180.0, 0.75,
            ),
            (
                "Consolidate S3 storage tiers — move cold data to Glacier",
                "Objects not accessed in 90+ days represent 40% of S3 spend. Lifecycle policy to Glacier saves ~70% on cold storage.",
                "production", "medium",
                ExperimentStatus.HYPOTHESIS,
                420.0, 0.68,
            ),
            (
                "Reduce BigQuery on-demand scans with partitioned tables",
                "Adding date partitioning to top 3 analytics tables reduces bytes scanned by ~60%.",
                "production", "low",
                ExperimentStatus.DRAFT,
                310.0, 0.79,
            ),
        ]

        now = datetime.now(timezone.utc)
        experiments: list[OptimizationExperiment] = []
        for title, hypothesis, env, criticality, status, savings, confidence in specs:
            exp = OptimizationExperiment(
                org_id=org_id,
                title=title,
                hypothesis=hypothesis,
                description=hypothesis,
                target_environment=env,
                target_criticality=criticality,
                status=status,
                simulated_savings_usd=round(savings * rng.uniform(0.9, 1.1), 2),
                simulated_confidence=round(confidence * rng.uniform(0.95, 1.05), 3),
                simulation_notes="Simulated via mock seed data.",
                guardrails={"max_blast_radius": 0.2, "rollback_on_error_rate": 0.05},
                estimated_risk_score=round(rng.uniform(0.1, 0.4), 2),
                started_at=now - timedelta(days=rng.randint(5, 20)) if status in (
                    ExperimentStatus.RUNNING, ExperimentStatus.CONCLUDED
                ) else None,
                concluded_at=now - timedelta(days=rng.randint(1, 4)) if status == ExperimentStatus.CONCLUDED else None,
                actual_savings_usd=round(savings * rng.uniform(0.85, 1.05), 2) if status == ExperimentStatus.CONCLUDED else None,
            )
            self.db.add(exp)
            experiments.append(exp)

        await self.db.flush()
        log.info("dev_seed.experiments_created", org_id=str(org_id), count=len(experiments))
        return experiments

    # ------------------------------------------------------------------
    # PostgreSQL — CostAnomalies
    # ------------------------------------------------------------------

    async def _create_cost_anomalies(
        self, org_id: UUID, cost_rows: list[dict[str, Any]], rng: random.Random
    ) -> list[CostAnomaly]:
        # Derive realistic mean costs per service from the generated cost_rows
        service_costs: dict[tuple[str, str], list[float]] = {}
        for r in cost_rows:
            key = (r["provider"], r["service"])
            service_costs.setdefault(key, []).append(float(r["cost_usd"]))

        today = date.today()
        anomalies: list[CostAnomaly] = []

        # Pick 4 services to have anomalies
        candidates = list(service_costs.keys())
        rng.shuffle(candidates)
        selected = candidates[:4]

        severity_map = [
            CostAnomalySeverity.HIGH,
            CostAnomalySeverity.MEDIUM,
            CostAnomalySeverity.MEDIUM,
            CostAnomalySeverity.LOW,
        ]

        for i, (provider, service) in enumerate(selected):
            costs = service_costs[(provider, service)]
            mean  = sum(costs) / len(costs)
            stddev = max(mean * 0.12, 0.01)
            spike_factor = rng.uniform(1.8, 2.8)
            current = round(mean * spike_factor, 4)
            z_score = round((current - mean) / stddev, 2)
            deviation_pct = round((current - mean) / mean * 100, 1)
            severity = severity_map[i]

            anomaly = CostAnomaly(
                org_id=org_id,
                provider=provider,
                service=service,
                observed_date=today - timedelta(days=i),  # distinct dates per anomaly
                current_cost_usd=current,
                historical_mean_usd=round(mean, 4),
                historical_stddev_usd=round(stddev, 4),
                z_score=z_score,
                deviation_pct=deviation_pct,
                severity=severity,
                window_days=30,
                z_threshold=2.0,
            )
            self.db.add(anomaly)
            anomalies.append(anomaly)

        await self.db.flush()
        log.info("dev_seed.anomalies_created", org_id=str(org_id), count=len(anomalies))
        return anomalies

    # ------------------------------------------------------------------
    # PostgreSQL — OptimizationOpportunities
    # ------------------------------------------------------------------

    async def _create_opportunities(
        self,
        org_id: UUID,
        accounts: tuple[CloudAccount, CloudAccount, CloudAccount],
        rng: random.Random,
    ) -> list[OptimizationOpportunity]:
        azure_acct, aws_acct, gcp_acct = accounts

        specs = [
            (
                azure_acct.id, "Virtual Machines", "eastus", "production", "platform",
                OpportunityCategory.RIGHTSIZING,
                "Right-size Standard_D4s_v3 VMs to Standard_D2s_v3",
                "Average CPU utilization is below 25% over the last 30 days. Downsizing to D2s_v3 reduces compute cost by ~40% with no performance impact.",
                320.0, RiskLevel.LOW, EffortLevel.LOW,
            ),
            (
                azure_acct.id, "Azure Kubernetes Service", "eastus", "production", "platform",
                OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
                "Switch AKS node pool to spot instances for non-prod workloads",
                "Non-production AKS node pools running on standard VMs can be migrated to spot instances, saving up to 80% on compute.",
                180.0, RiskLevel.MEDIUM, EffortLevel.MEDIUM,
            ),
            (
                aws_acct.id, "Amazon EC2", "us-east-1", "production", "platform",
                OpportunityCategory.RESERVED_INSTANCES,
                "Purchase 1-year reserved instances for steady-state EC2 fleet",
                "EC2 instances running 24/7 for 90+ days qualify for reserved instance pricing, saving ~35% vs on-demand.",
                450.0, RiskLevel.LOW, EffortLevel.LOW,
            ),
            (
                aws_acct.id, "Amazon S3", "us-east-1", "production", "data",
                OpportunityCategory.STORAGE_OPTIMIZATION,
                "Move S3 objects older than 90 days to Glacier Instant Retrieval",
                "40% of S3 storage has not been accessed in 90+ days. Lifecycle policy to Glacier saves ~70% on cold storage costs.",
                220.0, RiskLevel.LOW, EffortLevel.LOW,
            ),
            (
                gcp_acct.id, "Compute Engine", "us-central1", "production", "platform",
                OpportunityCategory.RESERVED_INSTANCES,
                "Commit to 1-year CUDs for Compute Engine baseline workloads",
                "Committed Use Discounts for stable Compute Engine workloads provide 37% savings vs on-demand pricing.",
                280.0, RiskLevel.LOW, EffortLevel.LOW,
            ),
            (
                gcp_acct.id, "BigQuery", "us-central1", "production", "analytics",
                OpportunityCategory.ARCHITECTURE_CHANGE,
                "Add date partitioning to top analytics tables to reduce scanned bytes",
                "Top 3 BigQuery tables lack partitioning. Adding date partitions reduces bytes scanned by ~60%, cutting on-demand query costs significantly.",
                120.0, RiskLevel.LOW, EffortLevel.MEDIUM,
            ),
            (
                azure_acct.id, "Azure Functions", "westus2", "development", "backend",
                OpportunityCategory.IDLE_RESOURCES,
                "Remove idle Azure Functions running on Premium plan",
                "3 Azure Functions on Premium plan have zero invocations in the last 30 days. Deleting or moving to Consumption plan eliminates idle costs.",
                96.0, RiskLevel.LOW, EffortLevel.LOW,
            ),
        ]

        opportunities: list[OptimizationOpportunity] = []
        for account_id, service, region, environment, owner_team, category, title, description, monthly_savings, risk, effort in specs:
            variance = rng.uniform(0.9, 1.1)
            monthly = round(monthly_savings * variance, 2)
            opp = OptimizationOpportunity(
                org_id=org_id,
                account_id=account_id,
                title=title,
                description=description,
                category=category,
                status=OpportunityStatus.OPEN,
                estimated_monthly_savings_usd=monthly,
                estimated_annual_savings_usd=round(monthly * 12, 2),
                current_monthly_cost_usd=round(monthly * rng.uniform(2.5, 4.0), 2),
                financial_impact_score=round(min(monthly / 10, 100), 1),
                risk_score=round(rng.uniform(5, 30), 1),
                effort_score=round(rng.uniform(10, 40), 1),
                criticality_score=round(rng.uniform(20, 80), 1),
                composite_score=round(rng.uniform(40, 90), 1),
                risk_level=risk,
                effort_level=effort,
                service=service,
                region=region,
                environment=environment,
                owner_team=owner_team,
                resource_id=f"/mock/{service.lower().replace(' ', '-')}-01",
                resource_name=f"mock-{service.lower().replace(' ', '-')}-01",
            )
            self.db.add(opp)
            opportunities.append(opp)

        await self.db.flush()
        log.info("dev_seed.opportunities_created", org_id=str(org_id), count=len(opportunities))
        return opportunities
