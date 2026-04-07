from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.domains.audit_chain.service import AuditChainService
from app.domains.cloud_accounts.models import CloudAccount, CloudProvider, ConnectorHealth, ConnectorStatus
from app.domains.cloud_accounts.schemas import AzureCredentials, CloudAccountCreate
from app.domains.cloud_accounts.validators import ScopeValidationResult

log = get_logger(__name__)


class CloudAccountService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    async def create_account(self, org_id: UUID, req: CloudAccountCreate) -> CloudAccount:
        credentials_encrypted = None
        if req.azure_credentials:
            credentials_encrypted = encrypt_secret(req.azure_credentials.model_dump_json())

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
            except PermissionError as exc:
                raise ValueError(str(exc)) from exc
            except Exception as exc:
                raise ValueError(
                    f"Could not authenticate with Azure using the provided credentials: {exc}"
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
        if account.provider != CloudProvider.AZURE:
            return ScopeValidationResult(
                ok=False,
                validated_scopes=[],
                message=f"Scope validation for provider '{account.provider.value}' is not implemented yet",
            )

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
        )

        try:
            await client.validate_connection()
            await client.validate_cost_management_scope(creds.subscription_id)
        except PermissionError as exc:
            return ScopeValidationResult(ok=False, validated_scopes=[], message=str(exc))
        except Exception as exc:
            return ScopeValidationResult(
                ok=False,
                validated_scopes=[],
                message=f"Could not validate scopes with provider API: {exc}",
            )

        scopes = ["CostManagementReaderOrHigher"]
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

    async def list_accounts(self, org_id: UUID) -> list[CloudAccount]:
        result = await self.db.execute(
            select(CloudAccount).where(CloudAccount.org_id == org_id).order_by(CloudAccount.created_at)
        )
        return list(result.scalars().all())

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
        raw = json.loads(decrypt_secret(account.credentials_encrypted))
        return AzureCredentials(**raw)

    async def run_health_check(self, account: CloudAccount) -> ConnectorHealth:
        from app.domains.connectors.azure.client import AzureConnectorClient

        start = time.monotonic()
        status = ConnectorStatus.ERROR
        message = None

        try:
            creds = await self.get_azure_credentials(account)
            client = AzureConnectorClient.from_account(account, creds)
            await client.validate_connection()
            status = ConnectorStatus.ACTIVE
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
