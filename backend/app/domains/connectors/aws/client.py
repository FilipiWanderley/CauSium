from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.connectors.base import BaseConnector, CanonicalCarbonRecord, CanonicalCostRecord, CanonicalEventRecord

log = get_logger(__name__)


class AwsConnectorClient(BaseConnector):
    """AWS connector using IAM access keys (phase 1)."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        *,
        session_token: str | None = None,
        region: str = "us-east-1",
    ):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.region = region

    @classmethod
    def from_account(cls, account, creds) -> "AwsConnectorClient":
        settings = get_settings()
        if creds:
            return cls(
                access_key_id=creds.access_key_id,
                secret_access_key=creds.secret_access_key,
                session_token=creds.session_token,
                region=creds.region or "us-east-1",
            )
        if settings.aws_credentials_available:
            return cls(
                access_key_id=settings.aws_access_key_id,
                secret_access_key=settings.aws_secret_access_key,
                session_token=settings.aws_session_token or None,
                region=settings.aws_region,
            )
        raise ValueError("AWS credentials are required for this account")

    def _client(self, service_name: str):
        return boto3.client(
            service_name,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            aws_session_token=self.session_token,
            region_name=self.region,
        )

    async def validate_connection(self) -> None:
        sts = self._client("sts")
        identity = sts.get_caller_identity()
        log.info("aws.validate_connection.ok", account=str(identity.get("Account") or "unknown"))

    async def validate_cost_management_scope(self, subscription_id: str) -> None:
        ce = self._client("ce")
        end = date.today()
        start = end - timedelta(days=1)
        try:
            ce.get_cost_and_usage(
                TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )
        except (ClientError, BotoCoreError) as exc:
            raise PermissionError(f"Could not access AWS Cost Explorer API: {exc}") from exc

    async def fetch_costs(self, subscription_id: str, start: date, end: date) -> list[CanonicalCostRecord]:
        ce = self._client("ce")
        rows: list[CanonicalCostRecord] = []

        paginator = ce.get_paginator("get_cost_and_usage")
        pages = paginator.paginate(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost", "UsageQuantity"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        for page in pages:
            rows.extend(self._normalize_cost_explorer_page(page, subscription_id))

        log.info("aws.fetch_costs.done", account=subscription_id, records=len(rows))
        return rows

    @staticmethod
    def _normalize_cost_explorer_page(page: dict, account_id: str) -> list[CanonicalCostRecord]:
        out: list[CanonicalCostRecord] = []
        for result in page.get("ResultsByTime", []):
            usage_date = datetime.strptime(result["TimePeriod"]["Start"], "%Y-%m-%d").date()
            groups = result.get("Groups", [])
            if not groups:
                groups = [{"Keys": ["AWS"], "Metrics": result.get("Total", {})}]
            for group in groups:
                metrics = group.get("Metrics", {})
                service = (group.get("Keys") or ["AWS"])[0]
                amount = float(metrics.get("UnblendedCost", {}).get("Amount", 0) or 0)
                usage = float(metrics.get("UsageQuantity", {}).get("Amount", 0) or 0)
                unit = str(metrics.get("UsageQuantity", {}).get("Unit", ""))
                currency = str(metrics.get("UnblendedCost", {}).get("Unit", "USD"))
                out.append(
                    CanonicalCostRecord(
                        date=usage_date,
                        provider="aws",
                        subscription_id=account_id,
                        service=service,
                        resource_id="",
                        resource_name="",
                        region="global",
                        environment="unknown",
                        owner_team="untagged",
                        cost_usd=amount,
                        usage_quantity=usage,
                        usage_unit=unit,
                        currency=currency,
                        tags={},
                    )
                )
        return out

    async def fetch_events(self, subscription_id: str, start: date, end: date) -> list[CanonicalEventRecord]:
        cloudtrail = self._client("cloudtrail")
        start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
        end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)

        paginator = cloudtrail.get_paginator("lookup_events")
        pages = paginator.paginate(StartTime=start_dt, EndTime=end_dt)

        rows: list[CanonicalEventRecord] = []
        for page in pages:
            for ev in page.get("Events", []):
                event_time = ev.get("EventTime")
                if isinstance(event_time, str):
                    try:
                        event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                    except Exception:
                        event_time = datetime.now(timezone.utc)
                if event_time is None:
                    event_time = datetime.now(timezone.utc)

                rows.append(
                    CanonicalEventRecord(
                        timestamp=event_time,
                        provider="aws",
                        subscription_id=subscription_id,
                        event_type=str(ev.get("EventName") or "unknown"),
                        resource_id="",
                        resource_name=str(ev.get("Username") or ""),
                        region=str(ev.get("AwsRegion") or "global"),
                        severity="informational",
                        description=str(ev.get("EventName") or ""),
                        caller=str(ev.get("Username") or ""),
                        correlation_id=str(ev.get("EventId") or ""),
                        raw_data=str(ev),
                    )
                )

        log.info("aws.fetch_events.done", account=subscription_id, records=len(rows))
        return rows

    async def fetch_carbon_emissions(
        self,
        subscription_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCarbonRecord]:
        # AWS carbon integration is out-of-scope for phase 1 in this connector.
        return []
