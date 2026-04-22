from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from importlib import import_module

import httpx

from app.core.config import get_settings
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


class GcpConnectorClient(BaseConnector):
    """GCP connector using service account JSON or workload identity (ADC)."""

    def __init__(
        self,
        service_account_json: str | None,
        project_id: str,
        *,
        use_workload_identity: bool = False,
        billing_export_table: str | None = None,
        logging_filter: str | None = None,
        carbon_footprint_table: str | None = None,
    ):
        self.service_account_json = service_account_json
        self.project_id = project_id
        self.use_workload_identity = use_workload_identity
        self.billing_export_table = billing_export_table
        self.logging_filter = logging_filter
        self.carbon_footprint_table = carbon_footprint_table
        self._credentials = None

    @classmethod
    def from_account(cls, account, creds) -> "GcpConnectorClient":
        settings = get_settings()
        if creds:
            return cls(
                service_account_json=creds.service_account_json,
                project_id=creds.project_id,
                use_workload_identity=bool(getattr(creds, "use_workload_identity", False)),
                billing_export_table=creds.billing_export_table,
                logging_filter=creds.logging_filter,
                carbon_footprint_table=settings.gcp_carbon_footprint_table or None,
            )
        if settings.gcp_credentials_available:
            return cls(
                service_account_json=settings.gcp_service_account_json or None,
                project_id=settings.gcp_project_id,
                use_workload_identity=settings.gcp_use_workload_identity,
                billing_export_table=settings.gcp_billing_export_table or None,
                logging_filter=settings.gcp_logging_filter or None,
                carbon_footprint_table=settings.gcp_carbon_footprint_table or None,
            )
        raise ValueError("GCP credentials are required for this account")

    def _get_credentials(self):
        if self._credentials is None:
            if self.use_workload_identity:
                google_auth = self._import_module("google.auth")
                creds, detected_project = google_auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                if detected_project and not self.project_id:
                    self.project_id = detected_project
                self._credentials = creds
            else:
                if not self.service_account_json:
                    raise ValueError(
                        "GCP service_account_json is required when use_workload_identity is false"
                    )
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
            resp = await self._get_with_retries(
                client,
                url,
                headers={"Authorization": f"Bearer {creds.token}"},
            )
            if resp is None:
                raise ValueError(f"Unable to access GCP project '{self.project_id}'")

    def _access_token(self) -> str:
        google_auth_request = self._import_symbol("google.auth.transport.requests", "Request")
        creds = self._get_credentials()
        creds.refresh(google_auth_request())
        return str(creds.token)

    @staticmethod
    def _configured_carbon_factors() -> dict[str, float]:
        raw = (get_settings().gcp_carbon_factors_json or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except ValueError:
            log.warning("gcp.carbon_factors.invalid_json")
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, float] = {}
        for key, value in parsed.items():
            try:
                out[str(key).lower()] = float(value)
            except (TypeError, ValueError):
                continue
        return out

    async def _get_with_retries(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        headers: dict[str, str],
        params: dict | None = None,
        allow_missing: bool = False,
    ) -> httpx.Response | None:
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            response = await client.get(url, headers=headers, params=params)
            if allow_missing and response.status_code in {403, 404}:
                return None
            if response.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts:
                delay_s = 0.5 * (2 ** (attempt - 1))
                log.warning(
                    "gcp.http.retry",
                    url=url,
                    status=response.status_code,
                    attempt=attempt,
                    delay_s=delay_s,
                )
                await asyncio.sleep(delay_s)
                continue
            response.raise_for_status()
            return response
        return None

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
        official = await self._fetch_carbon_from_bigquery(subscription_id, start, end)
        if official:
            log.info("gcp.fetch_carbon.official.done", project=self.project_id, records=len(official))
            return official

        try:
            costs = await self.fetch_costs(subscription_id, start, end)
        except Exception as exc:
            log.warning("gcp.fetch_carbon.failed", project=self.project_id, reason=str(exc))
            return []

        aggregated: dict[tuple[str, str], float] = {}
        for row in costs:
            year_month = row.date.strftime("%Y-%m")
            service = row.service or "unknown"
            factor = self._estimate_carbon_factor_kg_per_usd(service)
            kg = max(row.cost_usd, 0.0) * factor
            key = (year_month, service)
            aggregated[key] = aggregated.get(key, 0.0) + kg

        records = [
            CanonicalCarbonRecord(
                year_month=ym,
                provider="gcp",
                subscription_id=subscription_id,
                service=service,
                resource_group="global",
                kg_co2e=round(kg, 6),
            )
            for (ym, service), kg in sorted(aggregated.items(), key=lambda item: item[0])
            if kg > 0
        ]
        log.info("gcp.fetch_carbon.done", project=self.project_id, records=len(records))
        return records

    async def _fetch_carbon_from_bigquery(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCarbonRecord]:
        if not self.carbon_footprint_table:
            return []

        bigquery = self._import_module("google.cloud.bigquery")
        client = bigquery.Client(project=self.project_id, credentials=self._get_credentials())
        start_month = date(start.year, start.month, 1)
        end_month = date(end.year, end.month, 1)

        query = f"""
        SELECT
          FORMAT_DATE('%Y-%m', usage_month) AS year_month,
          IFNULL(service.description, 'unknown') AS service_name,
          SUM(carbon_footprint_total_kgCO2e) AS kg_co2e
        FROM `{self.carbon_footprint_table}`
        WHERE usage_month BETWEEN @start_month AND @end_month
        GROUP BY year_month, service_name
        ORDER BY year_month ASC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_month", "DATE", start_month.isoformat()),
                bigquery.ScalarQueryParameter("end_month", "DATE", end_month.isoformat()),
            ]
        )
        try:
            rows = client.query(query, job_config=job_config).result()
        except Exception as exc:
            log.warning(
                "gcp.fetch_carbon.official_query_failed",
                project=self.project_id,
                table=self.carbon_footprint_table,
                reason=str(exc),
            )
            return []

        out: list[CanonicalCarbonRecord] = []
        for row in rows:
            row_dict = dict(row)
            year_month = str(row_dict.get("year_month") or "")
            service = str(row_dict.get("service_name") or "unknown")
            try:
                kg = float(row_dict.get("kg_co2e") or 0)
            except (TypeError, ValueError):
                continue
            if len(year_month) != 7 or kg <= 0:
                continue
            out.append(
                CanonicalCarbonRecord(
                    year_month=year_month,
                    provider="gcp",
                    subscription_id=subscription_id,
                    service=service,
                    resource_group="global",
                    kg_co2e=kg,
                )
            )

        return out

    async def fetch_recommendations(
        self,
        subscription_id: str,
    ) -> list[CanonicalRecommendationRecord]:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        records: list[CanonicalRecommendationRecord] = []
        now = datetime.now(timezone.utc)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                recs_resp = await self._get_with_retries(
                    client,
                    f"https://recommender.googleapis.com/v1/projects/{self.project_id}/locations/-/recommenders",
                    headers=headers,
                )
                if recs_resp is None:
                    return []
                recs_resp.raise_for_status()
                recommenders = recs_resp.json().get("recommenders", [])
                for recommender in recommenders:
                    rec_name = str(recommender.get("name") or "")
                    if not rec_name:
                        continue
                    lowered = rec_name.lower()
                    if "cost" not in lowered and "idle" not in lowered and "machine" not in lowered:
                        continue
                    page_token: str | None = None
                    while True:
                        params = {"filter": 'stateInfo.state = "ACTIVE"', "pageSize": 100}
                        if page_token:
                            params["pageToken"] = page_token
                        response = await self._get_with_retries(
                            client,
                            f"https://recommender.googleapis.com/v1/{rec_name}/recommendations",
                            headers=headers,
                            params=params,
                            allow_missing=True,
                        )
                        if response is None:
                            break
                        response.raise_for_status()
                        payload = response.json()
                        for item in payload.get("recommendations", []):
                            name = str(item.get("name") or "")
                            description = str(item.get("description") or "")
                            subtype = str(item.get("recommenderSubtype") or "")
                            resource_id = self._parse_gcp_resource_id(item)
                            records.append(
                                CanonicalRecommendationRecord(
                                    recommendation_id=name or f"{rec_name}:{hash(description)}",
                                    provider="gcp",
                                    subscription_id=subscription_id,
                                    category="Cost",
                                    impact=self._parse_gcp_impact(item),
                                    resource_id=resource_id,
                                    resource_name=resource_id.split("/")[-1] if resource_id else "",
                                    resource_group="",
                                    service="Recommender",
                                    short_description=description,
                                    recommendation_type_id=subtype or rec_name.split("/")[-1],
                                    estimated_savings_usd=self._parse_gcp_estimated_savings(item),
                                    fetched_at=now,
                                )
                            )
                        page_token = payload.get("nextPageToken")
                        if not page_token:
                            break
        except Exception as exc:
            log.warning("gcp.fetch_recommendations.failed", project=self.project_id, reason=str(exc))
            return []

        log.info("gcp.fetch_recommendations.done", project=self.project_id, records=len(records))
        return records

    async def fetch_inventory(
        self,
        subscription_id: str,
    ) -> list[CanonicalResourceRecord]:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        now = datetime.now(timezone.utc)
        records: list[CanonicalResourceRecord] = []
        page_token: str | None = None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    params = {"maxResults": 500}
                    if page_token:
                        params["pageToken"] = page_token
                    response = await self._get_with_retries(
                        client,
                        f"https://compute.googleapis.com/compute/v1/projects/{self.project_id}/aggregated/instances",
                        headers=headers,
                        params=params,
                    )
                    if response is None:
                        break
                    response.raise_for_status()
                    payload = response.json()
                    for scoped in (payload.get("items") or {}).values():
                        for instance in scoped.get("instances", []) or []:
                            labels = {str(k): str(v) for k, v in (instance.get("labels") or {}).items()}
                            machine_type = str(instance.get("machineType") or "").split("/")[-1]
                            zone = str(instance.get("zone") or "").split("/")[-1]
                            records.append(
                                CanonicalResourceRecord(
                                    resource_id=str(instance.get("selfLink") or ""),
                                    provider="gcp",
                                    subscription_id=subscription_id,
                                    name=str(instance.get("name") or ""),
                                    resource_type="compute.instances",
                                    resource_group="",
                                    location=zone,
                                    environment=self._infer_environment(labels),
                                    owner_team=self._infer_owner_team(labels),
                                    sku_name=machine_type,
                                    sku_tier="",
                                    provisioning_state=str(instance.get("status") or "unknown").lower(),
                                    tags=labels,
                                    fetched_at=now,
                                )
                            )
                    page_token = payload.get("nextPageToken")
                    if not page_token:
                        break
        except Exception as exc:
            log.warning("gcp.fetch_inventory.failed", project=self.project_id, reason=str(exc))
            return []

        log.info("gcp.fetch_inventory.done", project=self.project_id, records=len(records))
        return records

    async def fetch_usage_metrics(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalUsageRecord]:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        records: list[CanonicalUsageRecord] = []
        start_ts = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).isoformat()
        end_ts = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
        page_token: str | None = None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    params = {
                        "filter": 'metric.type = "compute.googleapis.com/instance/cpu/utilization"',
                        "interval.startTime": start_ts,
                        "interval.endTime": end_ts,
                        "aggregation.alignmentPeriod": "86400s",
                        "aggregation.perSeriesAligner": "ALIGN_MEAN",
                        "view": "FULL",
                        "pageSize": 500,
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    response = await self._get_with_retries(
                        client,
                        f"https://monitoring.googleapis.com/v3/projects/{self.project_id}/timeSeries",
                        headers=headers,
                        params=params,
                        allow_missing=True,
                    )
                    if response is None:
                        break
                    response.raise_for_status()
                    payload = response.json()
                    for series in payload.get("timeSeries", []) or []:
                        resource_labels = (series.get("resource") or {}).get("labels") or {}
                        instance_id = str(resource_labels.get("instance_id") or "")
                        zone = str(resource_labels.get("zone") or "")
                        for point in series.get("points", []) or []:
                            end_time = (((point.get("interval") or {}).get("endTime") or "")).replace("Z", "+00:00")
                            value = ((point.get("value") or {}).get("doubleValue"))
                            if not end_time or value is None:
                                continue
                            dt = datetime.fromisoformat(end_time)
                            records.append(
                                CanonicalUsageRecord(
                                    date=dt.date(),
                                    provider="gcp",
                                    subscription_id=subscription_id,
                                    service="Compute Engine",
                                    resource_id=instance_id,
                                    metric_name="CPUUtilization",
                                    metric_value=float(value),
                                    metric_unit="1",
                                    region=zone,
                                    environment="unknown",
                                )
                            )
                    page_token = payload.get("nextPageToken")
                    if not page_token:
                        break
        except Exception as exc:
            log.warning("gcp.fetch_usage_metrics.failed", project=self.project_id, reason=str(exc))
            return []

        log.info("gcp.fetch_usage_metrics.done", project=self.project_id, records=len(records))
        return records

    @staticmethod
    def _parse_gcp_impact(payload: dict[str, object]) -> str:
        impact = ((payload.get("primaryImpact") or {}) if isinstance(payload, dict) else {}) or {}
        category = str((impact.get("category") or "")).lower()
        if "cost" in category:
            return "High"
        if "performance" in category:
            return "Medium"
        return "Low"

    @staticmethod
    def _parse_gcp_estimated_savings(payload: dict[str, object]) -> float | None:
        impact = ((payload.get("primaryImpact") or {}) if isinstance(payload, dict) else {}) or {}
        projection = ((impact.get("costProjection") or {}) if isinstance(impact, dict) else {}) or {}
        amount = ((projection.get("cost") or {}) if isinstance(projection, dict) else {}) or {}
        units = amount.get("units")
        nanos = amount.get("nanos")
        if units is None and nanos is None:
            return None
        try:
            value = float(units or 0) + (float(nanos or 0) / 1_000_000_000.0)
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_gcp_resource_id(payload: dict[str, object]) -> str:
        content = ((payload.get("content") or {}) if isinstance(payload, dict) else {}) or {}
        groups = content.get("operationGroups") if isinstance(content, dict) else None
        if not isinstance(groups, list):
            return ""
        for group in groups:
            operations = group.get("operations") if isinstance(group, dict) else None
            if not isinstance(operations, list):
                continue
            for operation in operations:
                if not isinstance(operation, dict):
                    continue
                resource = operation.get("resource")
                if resource:
                    return str(resource)
        return ""

    @staticmethod
    def _infer_environment(labels: dict[str, str]) -> str:
        for key in ("env", "environment", "Environment", "Env"):
            val = str(labels.get(key, "")).lower()
            if val in {"prod", "production"}:
                return "production"
            if val in {"staging", "stage"}:
                return "staging"
            if val in {"dev", "development"}:
                return "development"
        return "unknown"

    @staticmethod
    def _infer_owner_team(labels: dict[str, str]) -> str:
        for key in ("team", "owner", "squad", "Team", "Owner", "Squad"):
            val = labels.get(key)
            if val:
                return str(val)
        return "untagged"

    def _estimate_carbon_factor_kg_per_usd(self, service: str) -> float:
        token = service.lower()
        overrides = self._configured_carbon_factors()
        if token in overrides:
            return overrides[token]
        for key, value in overrides.items():
            if key == "default":
                continue
            if key and key in token:
                return value
        if "default" in overrides:
            return overrides["default"]
        if any(key in token for key in ("compute", "gke", "run", "functions")):
            return 0.4
        if any(key in token for key in ("sql", "spanner", "bigtable", "database")):
            return 0.34
        if any(key in token for key in ("storage", "filestore", "persistent disk")):
            return 0.2
        if any(key in token for key in ("network", "load balancing", "cdn")):
            return 0.17
        return 0.29
