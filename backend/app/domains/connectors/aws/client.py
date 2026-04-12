from __future__ import annotations

import csv
import gzip
import io
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
        cur_bucket: str | None = None,
        cur_prefix: str | None = None,
    ):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.region = region
        self.cur_bucket = cur_bucket
        self.cur_prefix = cur_prefix or ""
        self._last_cur_checkpoints: list[dict[str, str]] = []

    @classmethod
    def from_account(cls, account, creds) -> "AwsConnectorClient":
        settings = get_settings()
        if creds:
            return cls(
                access_key_id=creds.access_key_id,
                secret_access_key=creds.secret_access_key,
                session_token=creds.session_token,
                region=creds.region or "us-east-1",
                cur_bucket=creds.cur_bucket,
                cur_prefix=creds.cur_prefix,
            )
        if settings.aws_credentials_available:
            return cls(
                access_key_id=settings.aws_access_key_id,
                secret_access_key=settings.aws_secret_access_key,
                session_token=settings.aws_session_token or None,
                region=settings.aws_region,
                cur_bucket=settings.aws_cur_bucket or None,
                cur_prefix=settings.aws_cur_prefix or None,
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

    async def fetch_costs(
        self,
        subscription_id: str,
        start: date,
        end: date,
        *,
        checkpoint_keys: set[str] | None = None,
    ) -> list[CanonicalCostRecord]:
        if self.cur_bucket:
            rows = await self._fetch_costs_from_cur(
                subscription_id,
                start,
                end,
                checkpoint_keys=checkpoint_keys,
            )
            if rows:
                return rows

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

    async def _fetch_costs_from_cur(
        self,
        subscription_id: str,
        start: date,
        end: date,
        *,
        checkpoint_keys: set[str] | None,
    ) -> list[CanonicalCostRecord]:
        s3 = self._client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.cur_bucket, Prefix=self.cur_prefix)

        out: list[CanonicalCostRecord] = []
        self._last_cur_checkpoints = []
        known = checkpoint_keys or set()

        for page in pages:
            for obj in page.get("Contents", []):
                key = str(obj.get("Key") or "")
                etag = str(obj.get("ETag") or "").strip('"')
                if not key.endswith(".csv") and not key.endswith(".csv.gz"):
                    continue

                checkpoint_key = f"{key}:{etag}"
                if checkpoint_key in known:
                    continue

                data = s3.get_object(Bucket=self.cur_bucket, Key=key)["Body"].read()
                rows = self._parse_cur_csv_bytes(
                    data,
                    account_id=subscription_id,
                    start=start,
                    end=end,
                )
                if not rows:
                    continue

                out.extend(rows)
                self._last_cur_checkpoints.append(
                    {
                        "checkpoint_key": checkpoint_key,
                        "object_key": key,
                        "object_etag": etag,
                    }
                )

        log.info(
            "aws.fetch_costs.cur.done",
            account=subscription_id,
            records=len(out),
            checkpoints=len(self._last_cur_checkpoints),
        )
        return out

    @staticmethod
    def _parse_cur_csv_bytes(
        raw_bytes: bytes,
        *,
        account_id: str,
        start: date,
        end: date,
    ) -> list[CanonicalCostRecord]:
        try:
            decoded = gzip.decompress(raw_bytes).decode("utf-8")
        except Exception:
            decoded = raw_bytes.decode("utf-8")

        reader = csv.DictReader(io.StringIO(decoded))
        records: list[CanonicalCostRecord] = []
        for row in reader:
            rec = AwsConnectorClient._normalize_cur_row(row, account_id=account_id)
            if rec is None:
                continue
            if rec.date < start or rec.date > end:
                continue
            records.append(rec)
        return records

    @staticmethod
    def _normalize_cur_row(row: dict[str, str], *, account_id: str) -> CanonicalCostRecord | None:
        lower_map = {k.lower(): (v or "") for k, v in row.items()}
        usage_start = (
            lower_map.get("line_item_usage_start_date")
            or lower_map.get("identity_time_interval")
            or ""
        )
        if not usage_start:
            return None
        usage_date_raw = usage_start.split("T", 1)[0]
        try:
            usage_date = datetime.strptime(usage_date_raw, "%Y-%m-%d").date()
        except ValueError:
            return None

        cost_raw = lower_map.get("line_item_unblended_cost") or lower_map.get("line_item_blended_cost") or "0"
        try:
            cost = float(cost_raw)
        except ValueError:
            return None

        usage_qty_raw = lower_map.get("line_item_usage_amount") or "0"
        try:
            usage_qty = float(usage_qty_raw)
        except ValueError:
            usage_qty = 0.0

        service = lower_map.get("product_product_name") or lower_map.get("line_item_product_code") or "AWS"
        resource_id = lower_map.get("line_item_resource_id") or ""
        region = lower_map.get("product_region") or lower_map.get("line_item_availability_zone") or "global"
        environment = (
            lower_map.get("resource_tags_user_environment")
            or lower_map.get("resource_tags_user_env")
            or "unknown"
        )
        owner_team = lower_map.get("resource_tags_user_ownerteam") or "untagged"

        return CanonicalCostRecord(
            date=usage_date,
            provider="aws",
            subscription_id=lower_map.get("line_item_usage_account_id") or account_id,
            service=service,
            resource_id=resource_id,
            resource_name=resource_id,
            region=region,
            environment=environment,
            owner_team=owner_team,
            cost_usd=cost,
            usage_quantity=usage_qty,
            usage_unit=lower_map.get("pricing_unit") or "",
            currency=lower_map.get("line_item_currency_code") or "USD",
            tags={},
        )

    def consume_last_cur_checkpoints(self) -> list[dict[str, str]]:
        out = self._last_cur_checkpoints
        self._last_cur_checkpoints = []
        return out

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
