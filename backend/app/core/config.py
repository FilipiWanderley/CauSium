from __future__ import annotations
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production-at-least-32-chars"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://stratopulse:stratopulse_dev@localhost:5432/stratopulse"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_db: str = "stratopulse"
    clickhouse_secure: bool = False
    clickhouse_verify: bool = True

    # Azure
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_oidc_redirect_uri: str = "http://localhost:8000/api/v1/auth/oidc/azure/callback"
    azure_oidc_scopes: str = "openid profile email"

    # Frontend
    frontend_url: str = "http://localhost:5174"
    auth_cookie_access_name: str = "sp_access_token"
    auth_cookie_refresh_name: str = "sp_refresh_token"
    auth_cookie_domain: str = ""
    auth_cookie_path: str = "/"
    auth_cookie_samesite: str = "strict"
    auth_cookie_secure: bool | None = None
    passkey_rp_id: str = "localhost"
    passkey_rp_name: str = "NimbusOps Compass"
    passkey_allowed_origins: str = "http://localhost:5173,http://localhost:5174"

    # Encryption key (Fernet base64)
    encryption_key: str = "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItZGV2ZWxvcA=="

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Security hardening
    security_headers_enabled: bool = True
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_auth_ip_per_minute: int = 20
    rate_limit_api_ip_per_minute: int = 300
    rate_limit_api_tenant_per_minute: int = 1200

    # Startup enforcement
    force_secure_datastores_in_production: bool = True

    # Workers
    ingestion_interval_hours: int = 6
    scoring_interval_hours: int = 1
    audit_checkpoint_interval_minutes: int = 60
    audit_checkpoint_retention_count: int = 200

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def azure_credentials_available(self) -> bool:
        return bool(self.azure_tenant_id and self.azure_client_id and self.azure_client_secret)

    @property
    def passkey_allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.passkey_allowed_origins.split(",") if o.strip()]

    @property
    def auth_cookie_secure_effective(self) -> bool:
        if self.auth_cookie_secure is None:
            return self.is_production
        return self.auth_cookie_secure

    def validate_production_security(self) -> None:
        if not self.is_production or not self.force_secure_datastores_in_production:
            return

        db_url = self.database_url.lower()
        if "sslmode=" not in db_url:
            raise ValueError("DATABASE_URL must include sslmode in production")
        if not any(v in db_url for v in ("sslmode=require", "sslmode=verify-ca", "sslmode=verify-full")):
            raise ValueError("DATABASE_URL sslmode must be require/verify-ca/verify-full in production")

        if not self.redis_url.lower().startswith("rediss://"):
            raise ValueError("REDIS_URL must use rediss:// in production")

        if not self.clickhouse_secure:
            raise ValueError("CLICKHOUSE_SECURE must be true in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
