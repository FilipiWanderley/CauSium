from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decrypt_secret_for_org, encrypt_secret_for_org
from app.domains.audit_chain.service import AuditChainService
from app.domains.cloud_accounts.models import CloudAccount, CloudAccountSubscription, CloudProvider, ConnectorHealth, ConnectorStatus
from app.domains.admin.models import DlqMessage, DlqStatus
from app.domains.cloud_accounts.schemas import AwsCredentials, AzureCredentials, CloudAccountCreate, GcpCredentials
from app.domains.cloud_accounts.validators import ScopeValidationResult
from app.domains.connectors.factory import get_connector_for_account

log = get_logger(__name__)

_SUSPECT_PLACEHOLDER_SUBSCRIPTIONS = {
    "aaaaaaaa-0000-0000-0000-aaaaaaaaaaaa",
}


class CloudAccountService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    async def create_account(self, org_id: UUID, req: CloudAccountCreate) -> CloudAccount:
        credentials_encrypted = None
        if req.provider == CloudProvider.AZURE and req.azure_credentials:
            credentials_encrypted = await encrypt_secret_for_org(
                self.db,
                org_id,
                req.azure_credentials.model_dump_json(),
            )
        if req.provider == CloudProvider.AWS and req.aws_credentials:
            credentials_encrypted = await encrypt_secret_for_org(
                self.db,
                org_id,
                req.aws_credentials.model_dump_json(),
            )
        if req.provider == CloudProvider.GCP and req.gcp_credentials:
            credentials_encrypted = await encrypt_secret_for_org(
                self.db,
                org_id,
                req.gcp_credentials.model_dump_json(),
            )

        # SP-CL03: validate credentials before persisting — fail fast with clear error
        if req.provider == CloudProvider.AZURE and req.azure_credentials:
            from app.domains.connectors.azure.client import AzureConnectorClient

            client = AzureConnectorClient(
                tenant_id=req.azure_credentials.tenant_id,
                client_id=req.azure_credentials.client_id,
                client_secret=req.azure_credentials.client_secret,
            )
            try:
                await client.validate_connection()
                await client.validate_cost_management_scope(req.azure_credentials.subscription_id)
                await client.validate_storage_access()
            except PermissionError as exc:
                raise ValueError(str(exc)) from exc
            except Exception as exc:
                raise ValueError(
                    f"Could not authenticate with Azure using the provided credentials: {exc}"
                ) from exc
        if req.provider == CloudProvider.AWS and req.aws_credentials:
            from app.domains.connectors.aws.client import AwsConnectorClient

            client = AwsConnectorClient(
                access_key_id=req.aws_credentials.access_key_id,
                secret_access_key=req.aws_credentials.secret_access_key,
                session_token=req.aws_credentials.session_token,
                region=req.aws_credentials.region or "us-east-1",
                cur_bucket=req.aws_credentials.cur_bucket,
                cur_prefix=req.aws_credentials.cur_prefix,
            )
            try:
                await client.validate_connection()
                await client.validate_cost_management_scope(req.external_id)
            except PermissionError as exc:
                raise ValueError(str(exc)) from exc
            except Exception as exc:
                raise ValueError(
                    f"Could not authenticate with AWS using the provided credentials: {exc}"
                ) from exc
        if req.provider == CloudProvider.GCP and req.gcp_credentials:
            from app.domains.connectors.gcp.client import GcpConnectorClient

            client = GcpConnectorClient(
                service_account_json=req.gcp_credentials.service_account_json,
                project_id=req.gcp_credentials.project_id,
                use_workload_identity=req.gcp_credentials.use_workload_identity,
                billing_export_table=req.gcp_credentials.billing_export_table,
                logging_filter=req.gcp_credentials.logging_filter,
            )
            try:
                await client.validate_connection()
                await client.validate_cost_management_scope(req.external_id)
            except PermissionError as exc:
                raise ValueError(str(exc)) from exc
            except Exception as exc:
                raise ValueError(
                    f"Could not authenticate with GCP using the provided credentials: {exc}"
                ) from exc

        account = CloudAccount(
            org_id=org_id,
            provider=req.provider,
            external_id=req.external_id,
            display_name=req.display_name,
            tenant_id=req.tenant_id,
            credentials_encrypted=credentials_encrypted,
            status=ConnectorStatus.PENDING,
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        log.info("cloud_account.created", account_id=str(account.id), provider=req.provider)
        return account

    async def validate_account_scopes(self, account: CloudAccount) -> ScopeValidationResult:
        """SP-CL03: Validate minimum provider scopes for an existing credential.

        This endpoint is explicit and idempotent. On success we persist:
          - account.scopes_validated_at
          - account.validated_scopes (JSON list[str])
        """
        scopes: list[str] = []

        if account.provider == CloudProvider.AZURE:
            creds = await self.get_azure_credentials(account)
            if creds is None:
                return ScopeValidationResult(
                    ok=False,
                    validated_scopes=[],
                    message="Azure credentials not found for this account",
                )

            from app.domains.connectors.azure.client import AzureConnectorClient

            client = AzureConnectorClient(
                tenant_id=creds.tenant_id,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                storage_account_url=creds.storage_account_url,
                cost_export_container=creds.cost_export_container,
            )

            try:
                await client.validate_connection()
                await client.validate_cost_management_scope(creds.subscription_id)
                await client.validate_storage_access()
            except PermissionError as exc:
                return ScopeValidationResult(ok=False, validated_scopes=[], message=str(exc))
            except Exception as exc:
                return ScopeValidationResult(
                    ok=False,
                    validated_scopes=[],
                    message=f"Could not validate scopes with provider API: {exc}",
                )

            scopes = ["CredentialsValid", "CostManagementReaderOrHigher"]
            if creds.storage_account_url and creds.cost_export_container:
                scopes.append("StorageBlobDataReader")
        elif account.provider == CloudProvider.AWS:
            creds = await self.get_aws_credentials(account)
            if creds is None:
                return ScopeValidationResult(
                    ok=False,
                    validated_scopes=[],
                    message="AWS credentials not found for this account",
                )

            from app.domains.connectors.aws.client import AwsConnectorClient

            client = AwsConnectorClient(
                access_key_id=creds.access_key_id,
                secret_access_key=creds.secret_access_key,
                session_token=creds.session_token,
                region=creds.region or "us-east-1",
                cur_bucket=creds.cur_bucket,
                cur_prefix=creds.cur_prefix,
            )
            try:
                await client.validate_connection()
                await client.validate_cost_management_scope(account.external_id)
            except PermissionError as exc:
                return ScopeValidationResult(ok=False, validated_scopes=[], message=str(exc))
            except Exception as exc:
                return ScopeValidationResult(
                    ok=False,
                    validated_scopes=[],
                    message=f"Could not validate scopes with provider API: {exc}",
                )

            scopes = ["CredentialsValid", "CostExplorerRead"]
            if creds.cur_bucket:
                scopes.append("CurBucketRead")
        elif account.provider == CloudProvider.GCP:
            creds = await self.get_gcp_credentials(account)
            if creds is None:
                return ScopeValidationResult(
                    ok=False,
                    validated_scopes=[],
                    message="GCP credentials not found for this account",
                )

            from app.domains.connectors.gcp.client import GcpConnectorClient

            client = GcpConnectorClient(
                service_account_json=creds.service_account_json,
                project_id=creds.project_id,
                use_workload_identity=creds.use_workload_identity,
                billing_export_table=creds.billing_export_table,
                logging_filter=creds.logging_filter,
            )
            try:
                await client.validate_connection()
                await client.validate_cost_management_scope(account.external_id)
            except PermissionError as exc:
                return ScopeValidationResult(ok=False, validated_scopes=[], message=str(exc))
            except Exception as exc:
                return ScopeValidationResult(
                    ok=False,
                    validated_scopes=[],
                    message=f"Could not validate scopes with provider API: {exc}",
                )

            scopes = ["CredentialsValid"]
            if creds.billing_export_table:
                scopes.append("BillingExportRead")
            scopes.append("LoggingRead")
        else:
            return ScopeValidationResult(
                ok=False,
                validated_scopes=[],
                message=f"Unsupported provider '{account.provider.value}' for scope validation",
            )

        account.scopes_validated_at = datetime.now(timezone.utc)
        account.validated_scopes = json.dumps(scopes)
        await self.db.flush()
        await self.db.refresh(account)

        return ScopeValidationResult(
            ok=True,
            validated_scopes=scopes,
            message="Credential scopes validated successfully",
        )

    async def audit_create(self, org_id: UUID, actor_user_id: UUID, account: CloudAccount) -> None:
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="cloud_account.created",
            entity_type="cloud_account",
            entity_id=str(account.id),
            payload={
                "provider": account.provider.value,
                "external_id": account.external_id,
                "display_name": account.display_name,
            },
        )

    async def list_accounts(
        self, org_id: UUID, limit: int = 100, offset: int = 0
    ) -> tuple[list[CloudAccount], int]:
        total_result = await self.db.execute(
            select(func.count()).select_from(CloudAccount).where(CloudAccount.org_id == org_id)
        )
        total = total_result.scalar_one()
        result = await self.db.execute(
            select(CloudAccount)
            .where(CloudAccount.org_id == org_id)
            .order_by(CloudAccount.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def list_sync_status(self, org_id: UUID) -> list[dict]:
        accounts, _ = await self.list_accounts(org_id)
        if not accounts:
            return []

        account_ids = [a.id for a in accounts]

        latest_health_rows = await self.db.execute(
            select(
                ConnectorHealth.account_id,
                func.max(ConnectorHealth.checked_at).label("last_health_check_at"),
            )
            .where(ConnectorHealth.account_id.in_(account_ids))
            .group_by(ConnectorHealth.account_id)
        )
        latest_health_by_account = {
            row.account_id: row.last_health_check_at for row in latest_health_rows
        }

        dlq_rows = await self.db.execute(
            select(
                DlqMessage.account_id,
                func.count(DlqMessage.id).label("open_dlq_count"),
            )
            .where(
                DlqMessage.org_id == org_id,
                DlqMessage.status == DlqStatus.OPEN,
                DlqMessage.account_id.in_(account_ids),
            )
            .group_by(DlqMessage.account_id)
        )
        dlq_by_account = {
            row.account_id: int(row.open_dlq_count) for row in dlq_rows
        }

        items: list[dict] = []
        for account in accounts:
            open_dlq_count = dlq_by_account.get(account.id, 0)
            last_health_check_at = latest_health_by_account.get(account.id)
            needs_attention = account.status != ConnectorStatus.ACTIVE or open_dlq_count > 0
            items.append(
                {
                    "account_id": account.id,
                    "provider": account.provider,
                    "display_name": account.display_name,
                    "connector_status": account.status,
                    "last_sync_at": account.last_sync_at,
                    "last_health_check_at": last_health_check_at,
                    "open_dlq_count": open_dlq_count,
                    "needs_attention": needs_attention,
                }
            )

        return items

    async def get_account(self, org_id: UUID, account_id: UUID) -> CloudAccount | None:
        result = await self.db.execute(
            select(CloudAccount).where(CloudAccount.id == account_id, CloudAccount.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def delete_account(self, org_id: UUID, account_id: UUID, actor_user_id: UUID | None = None) -> bool:
        account = await self.get_account(org_id, account_id)
        if not account:
            return False
        if actor_user_id:
            await self.audit_chain.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type="cloud_account.deleted",
                entity_type="cloud_account",
                entity_id=str(account_id),
                payload={
                    "provider": account.provider.value,
                    "external_id": account.external_id,
                    "display_name": account.display_name,
                },
            )
        await self.db.delete(account)
        return True

    async def get_azure_credentials(self, account: CloudAccount) -> AzureCredentials | None:
        if account.provider != CloudProvider.AZURE or not account.credentials_encrypted:
            return None
        raw = json.loads(
            await decrypt_secret_for_org(
                self.db,
                account.org_id,
                account.credentials_encrypted,
            )
        )
        return AzureCredentials(**raw)

    async def get_aws_credentials(self, account: CloudAccount) -> AwsCredentials | None:
        if account.provider != CloudProvider.AWS or not account.credentials_encrypted:
            return None
        raw = json.loads(
            await decrypt_secret_for_org(
                self.db,
                account.org_id,
                account.credentials_encrypted,
            )
        )
        return AwsCredentials(**raw)

    async def get_gcp_credentials(self, account: CloudAccount) -> GcpCredentials | None:
        if account.provider != CloudProvider.GCP or not account.credentials_encrypted:
            return None
        raw = json.loads(
            await decrypt_secret_for_org(
                self.db,
                account.org_id,
                account.credentials_encrypted,
            )
        )
        return GcpCredentials(**raw)

    async def run_health_check(self, account: CloudAccount) -> ConnectorHealth:
        start = time.monotonic()
        status = ConnectorStatus.ERROR
        message = None

        try:
            creds = await self.get_azure_credentials(account)
            if account.provider == CloudProvider.AWS:
                creds = await self.get_aws_credentials(account)
            if account.provider == CloudProvider.GCP:
                creds = await self.get_gcp_credentials(account)
            client = get_connector_for_account(account, creds)
            await client.validate_connection()
            status = ConnectorStatus.ACTIVE
            if account.provider == CloudProvider.AZURE and creds is not None:
                # Best-effort role review for health output; never block connectivity.
                try:
                    await client.validate_cost_management_scope(creds.subscription_id)
                except Exception as exc:
                    log.warning(
                        "connector.health_check.azure_scope_validation_skipped",
                        account_id=str(account.id),
                        error=str(exc),
                    )
                warnings = getattr(client, "get_last_scope_warnings", lambda: [])()
                if warnings:
                    message = " ".join(warnings)[:500]
        except Exception as e:
            message = str(e)[:500]
            log.warning("connector.health_check.failed", account_id=str(account.id), error=str(e))

        latency_ms = int((time.monotonic() - start) * 1000)
        health = ConnectorHealth(
            account_id=account.id,
            status=status,
            latency_ms=latency_ms,
            message=message,
        )
        self.db.add(health)
        account.status = status
        account.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(health)
        return health

    async def get_latest_health(self, account_id: UUID) -> ConnectorHealth | None:
        result = await self.db.execute(
            select(ConnectorHealth)
            .where(ConnectorHealth.account_id == account_id)
            .order_by(ConnectorHealth.checked_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_health_history(self, account_id: UUID, limit: int = 20) -> list[ConnectorHealth]:
        result = await self.db.execute(
            select(ConnectorHealth)
            .where(ConnectorHealth.account_id == account_id)
            .order_by(ConnectorHealth.checked_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_subscriptions(
        self,
        org_id: UUID,
        account_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[CloudAccountSubscription], int]:
        base = select(CloudAccountSubscription).where(
            CloudAccountSubscription.org_id == org_id
        )
        count_base = select(func.count()).select_from(CloudAccountSubscription).where(
            CloudAccountSubscription.org_id == org_id
        )
        if account_id is not None:
            base = base.where(CloudAccountSubscription.cloud_account_id == account_id)
            count_base = count_base.where(
                CloudAccountSubscription.cloud_account_id == account_id
            )
        total_result = await self.db.execute(count_base)
        total = total_result.scalar_one()
        result = await self.db.execute(
            base.order_by(CloudAccountSubscription.created_at).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_subscription(
        self,
        org_id: UUID,
        subscription_id: str,
        account_id: UUID | None = None,
    ) -> CloudAccountSubscription | None:
        q = select(CloudAccountSubscription).where(
            CloudAccountSubscription.org_id == org_id,
            CloudAccountSubscription.subscription_id == subscription_id,
        )
        if account_id is not None:
            q = q.where(CloudAccountSubscription.cloud_account_id == account_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def discover_subscriptions_from_cost_facts(
        self,
        org_id: UUID,
        account_id: UUID | None = None,
        provider: str | None = None,
    ) -> dict:
        """Read-only discovery with defensive filtering for suspicious subscriptions."""
        from app.core.clickhouse import execute_query

        where_parts = [
            "org_id = {org_id:String}",
        ]
        params: dict = {"org_id": str(org_id)}
        if account_id is not None:
            where_parts.append("account_id = {account_id:String}")
            params["account_id"] = str(account_id)
        if provider is not None:
            where_parts.append("provider = {provider:String}")
            params["provider"] = provider

        where_clause = " AND ".join(where_parts)
        try:
            rows = execute_query(
                f"""
                SELECT DISTINCT
                    account_id,
                    provider,
                    subscription_id
                FROM cost_facts
                WHERE {where_clause}
                ORDER BY account_id, subscription_id
                """,
                params,
            )
        except Exception as exc:
            log.warning("subscription.discover.clickhouse_failed", error=str(exc))
            return {
                "org_id": str(org_id),
                "discovered_count": 0,
                "skipped_count": 0,
                "subscriptions": [],
                "skipped_subscriptions": [],
            }

        # Load registered cloud_accounts to resolve cloud_tenant_id
        accounts, _ = await self.list_accounts(org_id)
        account_map = {str(a.id): a for a in accounts}

        result = []
        skipped = []
        for r in rows:
            acc_id = str(r.get("account_id") or "")
            sub_id = str(r.get("subscription_id") or "").strip()
            provider_value = str(r.get("provider") or "")
            acct = account_map.get(acc_id)
            row_out = {
                "org_id": str(org_id),
                "cloud_account_id": acc_id,
                "provider": provider_value,
                "cloud_tenant_id": acct.tenant_id if acct else None,
                "subscription_id": sub_id,
                "already_registered": False,
            }

            if not sub_id:
                row_out["skipped_reason"] = "empty_subscription_id"
                skipped.append(row_out)
                continue
            if sub_id.lower() in _SUSPECT_PLACEHOLDER_SUBSCRIPTIONS:
                row_out["skipped_reason"] = "invalid_placeholder_subscription"
                skipped.append(row_out)
                continue
            if acct is None:
                row_out["skipped_reason"] = "orphan_account"
                skipped.append(row_out)
                continue

            row_out["skipped_reason"] = None
            result.append(row_out)

        return {
            "org_id": str(org_id),
            "discovered_count": len(result),
            "skipped_count": len(skipped),
            "subscriptions": result,
            "skipped_subscriptions": skipped,
        }

    async def backfill_subscriptions_from_cost_facts(
        self,
        org_id: UUID,
        account_id: UUID | None = None,
        provider: str | None = None,
        dry_run: bool = True,
    ) -> dict:
        """
        Upsert discovered subscriptions into cloud_account_subscriptions.
        dry_run=True (default): returns preview without writing.
        dry_run=False: performs idempotent upsert.
        Status logic:
          - New rows: status=discovered
          - Existing rows: preserve status if already active/inactive/removed;
            only update last_seen_at and fill empty name fields.
        """
        from datetime import datetime, timezone
        from app.domains.cloud_accounts.models import SubscriptionStatus

        discovery = await self.discover_subscriptions_from_cost_facts(
            org_id, account_id=account_id, provider=provider
        )
        discovered = discovery["subscriptions"]
        skipped_rows = list(discovery["skipped_subscriptions"])

        # Load existing registrations for this org
        existing_result = await self.db.execute(
            select(CloudAccountSubscription).where(
                CloudAccountSubscription.org_id == org_id
            )
        )
        existing = existing_result.scalars().all()
        # Key: (cloud_account_id, provider, subscription_id)
        existing_map = {
            (str(s.cloud_account_id), s.provider.value, s.subscription_id): s
            for s in existing
        }

        # Load cloud_accounts for tenant_id resolution
        accounts, _ = await self.list_accounts(org_id)
        account_map = {str(a.id): a for a in accounts}

        now = datetime.now(timezone.utc)
        inserted = 0
        updated = 0
        skipped = len(skipped_rows)
        rows_out = []

        for row in discovered:
            acc_id = row["cloud_account_id"]
            prov = row["provider"]
            sub_id = row["subscription_id"]
            tenant_id = row["cloud_tenant_id"]

            if not acc_id or not sub_id:
                skipped += 1
                skipped_rows.append({
                    "org_id": str(org_id),
                    "cloud_account_id": acc_id,
                    "provider": prov,
                    "cloud_tenant_id": tenant_id,
                    "subscription_id": sub_id,
                    "already_registered": False,
                    "skipped_reason": "empty_subscription_id",
                })
                continue

            # Validate cloud_account belongs to this org
            acct = account_map.get(acc_id)
            if acct is None:
                skipped += 1
                skipped_rows.append({
                    "org_id": str(org_id),
                    "cloud_account_id": acc_id,
                    "provider": prov,
                    "cloud_tenant_id": tenant_id,
                    "subscription_id": sub_id,
                    "already_registered": False,
                    "skipped_reason": "orphan_account",
                })
                continue

            key = (acc_id, prov, sub_id)
            already = existing_map.get(key)
            already_registered = already is not None

            rows_out.append({
                "org_id": str(org_id),
                "cloud_account_id": acc_id,
                "provider": prov,
                "cloud_tenant_id": tenant_id,
                "subscription_id": sub_id,
                "already_registered": already_registered,
                "skipped_reason": None,
            })

            if dry_run:
                continue

            if already is None:
                # Insert new row
                from app.domains.cloud_accounts.models import CloudProvider
                try:
                    prov_enum = CloudProvider(prov)
                except ValueError:
                    skipped += 1
                    continue
                new_sub = CloudAccountSubscription(
                    org_id=org_id,
                    cloud_account_id=acct.id,
                    provider=prov_enum,
                    cloud_tenant_id=tenant_id,
                    subscription_id=sub_id,
                    subscription_name=None,
                    display_name=None,
                    status=SubscriptionStatus.DISCOVERED,
                    last_seen_at=now,
                )
                self.db.add(new_sub)
                inserted += 1
            else:
                # Update last_seen_at; preserve status unless it's still discovered
                already.last_seen_at = now
                if already.status == SubscriptionStatus.DISCOVERED:
                    pass  # keep as discovered — no promotion without explicit action
                # Fill empty name fields if still blank
                if not already.subscription_name:
                    already.subscription_name = None
                if not already.display_name:
                    already.display_name = None
                updated += 1

        if not dry_run:
            await self.db.flush()

        return {
            "org_id": str(org_id),
            "dry_run": dry_run,
            "discovered_count": len(rows_out),
            "inserted_count": inserted,
            "updated_count": updated,
            "skipped_count": skipped,
            "subscriptions": rows_out,
            "skipped_subscriptions": skipped_rows,
        }
