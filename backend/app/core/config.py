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

    # TLS enforcement for datastores (SP-A07)
    # PostgreSQL — ssl.SSLContext is injected into asyncpg when enabled or in production.
    db_ssl_enabled: bool = False
    db_ssl_verify: bool = True
    db_ssl_ca_file: str = ""
    db_ssl_min_version: str = "TLSv1.3"

    # Redis — ssl.SSLContext is injected when the URL scheme is rediss://.
    redis_ssl_verify: bool = True
    redis_ssl_ca_file: str = ""
    redis_ssl_min_version: str = "TLSv1.3"

    # ClickHouse — ca_cert pins the server certificate.
    # TLS minimum version is enforced server-side via ClickHouse config.xml
    # <disableProtocols>sslv2,sslv3,tlsv1,tlsv1_1,tlsv1_2</disableProtocols>.
    clickhouse_ca_cert: str = ""
    clickhouse_ssl_min_version: str = "TLSv1.3"

    # Azure
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_oidc_redirect_uri: str = "http://localhost:8000/api/v1/auth/oidc/azure/callback"
    azure_oidc_scopes: str = "openid profile email"
    # JWKS cache TTL in seconds — fetch at most once per period to avoid hammering
    # Microsoft's well-known endpoint while still picking up key rotations promptly.
    oidc_jwks_cache_ttl_seconds: int = 300

    # Frontend
    frontend_url: str = "http://localhost:5174"
    auth_cookie_access_name: str = "sp_access_token"
    auth_cookie_refresh_name: str = "sp_refresh_token"
    auth_cookie_domain: str = ""
    auth_cookie_path: str = "/"
    auth_cookie_samesite: str = "strict"
    auth_cookie_secure: bool | None = None
    passkey_rp_id: str = "localhost"
    passkey_rp_name: str = "StratoPulse"
    passkey_allowed_origins: str = "http://localhost:5173,http://localhost:5174"

    # SMTP (SP-AP03)
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@stratopulse.local"
    smtp_from_name: str = "StratoPulse"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10
    # Comma-separated recipients for operational critical alerts.
    smtp_alert_to: str = ""

    # Encryption key (Fernet base64)
    encryption_key: str = "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItZGV2ZWxvcA=="

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # SP-A04: Origin / Referer validation on auth state-mutation endpoints.
    # Provides defense-in-depth against CSRF for clients that bypass SameSite=Strict.
    # In production, requests without a recognisable Origin/Referer are rejected.
    # In non-production environments they are logged and allowed through, so that
    # automated API tests (which send no browser headers) continue to work.
    origin_validation_enabled: bool = True

    # Security hardening
    security_headers_enabled: bool = True
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "media-src 'none'; "
        "object-src 'none'; "
        "frame-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests"
    )
    permissions_policy: str = (
        "accelerometer=(), "
        "ambient-light-sensor=(), "
        "autoplay=(), "
        "battery=(), "
        "camera=(), "
        "cross-origin-isolated=(), "
        "display-capture=(), "
        "document-domain=(), "
        "encrypted-media=(), "
        "execution-while-not-rendered=(), "
        "execution-while-out-of-viewport=(), "
        "fullscreen=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "keyboard-map=(), "
        "magnetometer=(), "
        "microphone=(), "
        "midi=(), "
        "navigation-override=(), "
        "payment=(), "
        "picture-in-picture=(), "
        "publickey-credentials-get=(self), "
        "screen-wake-lock=(), "
        "sync-xhr=(), "
        "usb=(), "
        "web-share=(), "
        "xr-spatial-tracking=()"
    )
    # HSTS: 1 year, includeSubDomains. 'preload' intentionally omitted until
    # the domain is registered in the HSTS preload list.
    hsts_max_age: int = 31_536_000

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_trusted_proxy_header: str = "X-Forwarded-For"
    rate_limit_auth_ip_per_minute: int = 20
    rate_limit_auth_login_ip_per_window: int = 10
    rate_limit_auth_email_per_window: int = 5
    rate_limit_api_ip_per_minute: int = 300
    rate_limit_api_tenant_per_minute: int = 1200

    # Startup enforcement
    force_secure_datastores_in_production: bool = True

    # Workers
    ingestion_interval_hours: int = 6
    scoring_interval_hours: int = 1
    audit_checkpoint_interval_minutes: int = 60
    audit_checkpoint_retention_count: int = 200
    report_exports_dir: str = ".data/report-exports"
    report_export_retention_hours: int = 24
    workspace_key_rotation_interval_minutes: int = 60
    workspace_key_max_age_days: int = 30
    workspace_key_rotation_batch_size: int = 200

    @property
    def hsts_header_value(self) -> str:
        return f"max-age={self.hsts_max_age}; includeSubDomains"

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
    def smtp_alert_to_list(self) -> List[str]:
        return [o.strip() for o in self.smtp_alert_to.split(",") if o.strip()]

    @property
    def auth_cookie_secure_effective(self) -> bool:
        if self.auth_cookie_secure is None:
            return self.is_production
        return self.auth_cookie_secure

    def validate_production_security(self) -> None:
        if not self.is_production or not self.force_secure_datastores_in_production:
            return

        if self.secret_key == "change-me-in-production-at-least-32-chars":
            raise ValueError("SECRET_KEY must be changed from the default value in production")
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")

        if not self.security_headers_enabled:
            raise ValueError("SECURITY_HEADERS_ENABLED must be true in production")

        db_url = self.database_url.lower()
        if "sslmode=" not in db_url:
            raise ValueError("DATABASE_URL must include sslmode in production")
        if not any(v in db_url for v in ("sslmode=require", "sslmode=verify-ca", "sslmode=verify-full")):
            raise ValueError("DATABASE_URL sslmode must be require/verify-ca/verify-full in production")

        if not self.redis_url.lower().startswith("rediss://"):
            raise ValueError("REDIS_URL must use rediss:// in production")

        if not self.clickhouse_secure:
            raise ValueError("CLICKHOUSE_SECURE must be true in production")

        if "upgrade-insecure-requests" not in self.csp_policy:
            raise ValueError(
                "CSP_POLICY must include 'upgrade-insecure-requests' in production"
            )

        if self.hsts_max_age < 31_536_000:
            raise ValueError(
                "HSTS_MAX_AGE must be at least 31536000 (1 year) in production"
            )

        if self.db_ssl_min_version != "TLSv1.3":
            raise ValueError("DB_SSL_MIN_VERSION must be TLSv1.3 in production")

        if self.redis_ssl_min_version != "TLSv1.3":
            raise ValueError("REDIS_SSL_MIN_VERSION must be TLSv1.3 in production")

        if not self.clickhouse_verify:
            raise ValueError("CLICKHOUSE_VERIFY must be true in production")

        if self.clickhouse_ssl_min_version != "TLSv1.3":
            raise ValueError(
                "CLICKHOUSE_SSL_MIN_VERSION must be TLSv1.3 in production "
                "(enforce via ClickHouse config.xml disableProtocols)"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
