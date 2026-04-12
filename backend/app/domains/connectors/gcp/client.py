from __future__ import annotations

import json
from datetime import date, datetime, timezone
from importlib import import_module

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.connectors.base import BaseConnector, CanonicalCarbonRecord, CanonicalCostRecord, CanonicalEventRecord

log = get_logger(__name__)


class GcpConnectorClient(BaseConnector):
    """GCP connector using service account credentials (phase 1)."""

    def __init__(
        self,
        service_account_json: str,
        project_id: str,
        *,
        billing_export_table: str | None = None,
        logging_filter: str | None = None,
    ):
        self.service_account_json = service_account_json
        self.project_id = project_id
        self.billing_export_table = billing_export_table
        self.logging_filter = logging_filter
        self._credentials = None

    @classmethod
    def from_account(cls, account, creds) -> "GcpConnectorClient":
        settings = get_settings()
        if creds:
            return cls(
                service_account_json=creds.service_account_json,
                project_id=creds.project_id,
                billing_export_table=creds.billing_export_table,
                logging_filter=creds.logging_filter,
            )
        if settings.gcp_credentials_available:
            return cls(
                service_account_json=settings.gcp_service_account_json,
                project_id=settings.gcp_project_id,
                billing_export_table=settings.gcp_billing_export_table or None,
                logging_filter=settings.gcp_logging_filter or None,
            )
        raise ValueError("GCP credentials are required for this account")

    def _get_credentials(self):
        if self._credentials is None:
            service_account = self._import_module("google.oauth2.service_account")
            info = json.loads(self.service_account_json)
            self._credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        return self._credentials

    @staticmethod
    def _import_module(module_name: str):
        try:
            return import_module(module_name)
        except Exception as exc:
            raise RuntimeError(
                "GCP connector dependencies are missing. Install google-auth, "
                "google-cloud-bigquery and google-cloud-logging."
            ) from exc

    @staticmethod
    def _import_symbol(module_name: str, symbol_name: str):
        module = GcpConnectorClient._import_module(module_name)
        return getattr(module, symbol_name)

    async def validate_connection(self) -> None:
        google_auth_request = self._import_symbol(
            "google.auth.transport.requests", "Request"
        )
        creds = self._get_credentials()
        creds.refresh(google_auth_request())

        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{self.project_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {creds.token}"})
            if resp.status_code >= 400:
                raise ValueError(f"Unable to access GCP project '{self.project_id}': {resp.text}")

    async def validate_cost_management_scope(self, subscription_id: str) -> None:
        if not self.billing_export_table:
            # Billing export is optional in phase 1.
            return

        bigquery = self._import_module("google.cloud.bigquery")
        client = bigquery.Client(project=self.project_id, credentials=self._get_credentials())
        query = f"SELECT 1 FROM `{self.billing_export_table}` LIMIT 1"
        try:
            list(client.query(query).result())
        except Exception as exc:
            raise PermissionError(
                f"Could not query GCP billing export table '{self.billing_export_table}': {exc}"
            ) from exc

    async def fetch_costs(self, subscription_id: str, start: date, end: date) -> list[CanonicalCostRecord]:
        if not self.billing_export_table:
            return []

        bigquery = self._import_module("google.cloud.bigquery")
        client = bigquery.Client(project=self.project_id, credentials=self._get_credentials())
        query = f"""
        SELECT
          DATE(usage_start_time) AS usage_date,
          IFNULL(project.id, @project_id) AS project_id,
          IFNULL(service.description, 'unknown') AS service_name,
          IFNULL(resource.name, '') AS resource_name,
          IFNULL(location.region, 'global') AS region,
          SUM(cost) AS cost,
          ANY_VALUE(currency) AS currency
        FROM `{self.billing_export_table}`
        WHERE DATE(usage_start_time) BETWEEN @start_date AND @end_date
          AND IFNULL(project.id, @project_id) = @project_id
        GROUP BY usage_date, project_id, service_name, resource_name, region
        ORDER BY usage_date
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", start.isoformat()),
                bigquery.ScalarQueryParameter("end_date", "DATE", end.isoformat()),
                bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id),
            ]
        )

        rows = client.query(query, job_config=job_config).result()
        records = [self._normalize_billing_row(dict(r), self.project_id) for r in rows]
        records = [r for r in records if r is not None]
        log.info("gcp.fetch_costs.done", project_id=self.project_id, records=len(records))
        return records

    @staticmethod
    def _normalize_billing_row(row: dict, fallback_project_id: str) -> CanonicalCostRecord | None:
        usage_date = row.get("usage_date")
        if usage_date is None:
            return None
        if isinstance(usage_date, str):
            try:
                usage_date = datetime.strptime(usage_date, "%Y-%m-%d").date()
            except ValueError:
                return None

        try:
            cost = float(row.get("cost") or 0)
        except (TypeError, ValueError):
            return None

        return CanonicalCostRecord(
            date=usage_date,
            provider="gcp",
            subscription_id=str(row.get("project_id") or fallback_project_id),
            service=str(row.get("service_name") or "unknown"),
            resource_id="",
            resource_name=str(row.get("resource_name") or ""),
            region=str(row.get("region") or "global"),
            environment="unknown",
            owner_team="untagged",
            cost_usd=cost,
            usage_quantity=0.0,
            usage_unit="",
            currency=str(row.get("currency") or "USD"),
            tags={},
        )

    async def fetch_events(self, subscription_id: str, start: date, end: date) -> list[CanonicalEventRecord]:
        logging_v2 = self._import_module("google.cloud.logging_v2")
        client = logging_v2.Client(project=self.project_id, credentials=self._get_credentials())
        start_str = f"{start.isoformat()}T00:00:00Z"
        end_str = f"{end.isoformat()}T23:59:59Z"
        base_filter = f'timestamp >= "{start_str}" AND timestamp <= "{end_str}"'
        query_filter = f"({self.logging_filter}) AND {base_filter}" if self.logging_filter else base_filter

        records: list[CanonicalEventRecord] = []
        for entry in client.list_entries(filter_=query_filter, page_size=200):
            ts = getattr(entry, "timestamp", None) or datetime.now(timezone.utc)
            event_type = getattr(entry, "resource", None)
            resource_type = getattr(event_type, "type", "unknown") if event_type else "unknown"
            payload = getattr(entry, "payload", {})
            records.append(
                CanonicalEventRecord(
                    timestamp=ts,
                    provider="gcp",
                    subscription_id=self.project_id,
                    event_type=str(resource_type),
                    resource_id="",
                    resource_name="",
                    region="global",
                    severity="informational",
                    description=str(payload)[:500],
                    caller="",
                    correlation_id=str(getattr(entry, "insert_id", "")),
                    raw_data=str(payload),
                )
            )

        log.info("gcp.fetch_events.done", project_id=self.project_id, records=len(records))
        return records

    async def fetch_carbon_emissions(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCarbonRecord]:
        # Dedicated GCP carbon API integration remains out-of-scope for phase 1.
        return []
