from __future__ import annotations
from functools import lru_cache
import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Support both launch modes:
        # - project root cwd -> .env
        # - backend cwd      -> ../.env
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production-at-least-32-chars"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # PostgreSQL (explicit env var in production; fallback for staging)
    database_url: str = ""
    sqlite_fallback_url: str = "sqlite+aiosqlite:///./test.db"

    # Redis (optional in staging fallback mode)
    redis_url: str = ""

    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_db: str = "causium"
    clickhouse_secure: bool = False
    clickhouse_verify: bool = True

    # TLS enforcement for datastores (SP-A07)
    # PostgreSQL — ssl.SSLContext is injected into asyncpg when explicitly enabled.
    db_ssl_enabled: bool = False
    db_ssl_verify: bool = True
    db_ssl_ca_file: str = ""
    db_ssl_min_version: str = "TLSv1.3"

    # Redis — TLS params are passed to redis.asyncio.from_url when using rediss://.
    redis_ssl_verify: bool = True
    redis_ssl_ca_file: str = ""
    redis_ssl_min_version: str = "TLSv1.2"

    # ClickHouse — ca_cert pins the server certificate.
    # TLS minimum version is enforced server-side via ClickHouse config.xml
    # <disableProtocols>sslv2,sslv3,tlsv1,tlsv1_1,tlsv1_2</disableProtocols>.
    clickhouse_ca_cert: str = ""
    clickhouse_ssl_min_version: str = "TLSv1.3"

    # Azure
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_carbon_api_url: str = ""
    # Multi-subscription ingest. Off by default — enable explicitly in staging/prod.
    azure_multi_subscription_enabled: bool = False
    # Optional comma-separated allowlist of subscription IDs to ingest.
    # When set, only these subscriptions are ingested regardless of SP access.
    # When empty and multi-subscription is enabled, all accessible subscriptions are ingested.
    azure_allowed_subscription_ids: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_region: str = "us-east-1"
    aws_cur_bucket: str = ""
    aws_cur_prefix: str = ""
    # Optional AWS carbon export location (CSV/CSV.GZ). When set, carbon ingestion
    # will prefer this provider dataset before cost-based estimation.
    aws_carbon_export_bucket: str = ""
    aws_carbon_export_prefix: str = ""
    # Optional JSON map for kgCO2e per USD factors by AWS service token.
    # Example: {"ec2": 0.45, "s3": 0.2, "default": 0.3}
    aws_carbon_factors_json: str = ""
    gcp_service_account_json: str = ""
    gcp_project_id: str = ""
    gcp_use_workload_identity: bool = False
    gcp_billing_export_table: str = ""
    gcp_logging_filter: str = ""
    # Optional GCP Carbon Footprint BigQuery table.
    # Expected schema follows Cloud Carbon Footprint export conventions.
    gcp_carbon_footprint_table: str = ""
    # Optional JSON map for kgCO2e per USD factors by GCP service token.
    # Example: {"compute": 0.42, "storage": 0.19, "default": 0.29}
    gcp_carbon_factors_json: str = ""
    azure_oidc_redirect_uri: str = "http://localhost:8000/api/v1/auth/oidc/azure/callback"
    azure_oidc_scopes: str = "openid profile email"
    # JWKS cache TTL in seconds — fetch at most once per period to avoid hammering
    # Microsoft's well-known endpoint while still picking up key rotations promptly.
    oidc_jwks_cache_ttl_seconds: int = 300

    # LGPD / Terms of Service
    # Increment this value when terms change — users with an older version
    # will be required to re-accept before accessing the application.
    current_terms_version: str = "1.0"
    # DPO (Data Protection Officer) contact information
    dpo_email: str = "dpo@causium.io"
    dpo_instructions: str = (
        "To exercise your data protection rights (access, correction, deletion, portability), "
        "send an email to the DPO address above with your registered email and a description "
        "of your request. We will respond within 15 business days as required by LGPD Art. 18."
    )

    # Frontend
    frontend_url: str = "http://localhost:5174"
    auth_cookie_access_name: str = "sp_access_token"
    auth_cookie_refresh_name: str = "sp_refresh_token"
    auth_cookie_domain: str = ""
    auth_cookie_path: str = "/"
    auth_cookie_samesite: str = "strict"
    auth_cookie_secure: bool | None = None
    passkey_rp_id: str = "localhost"
    passkey_rp_name: str = "CauSium"
    passkey_allowed_origins: str = (
        "http://localhost:5173,"
        "http://localhost:5174,"
        "https://causium-api-2026-fea3frguggasbcg3.brazilsouth-01.azurewebsites.net"
    )

    # SMTP (SP-AP03)
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@causium.local"
    smtp_from_name: str = "CauSium"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10
    # Comma-separated recipients for operational critical alerts.
    smtp_alert_to: str = ""

    # Encryption key (Fernet base64)
    encryption_key: str = "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItZGV2ZWxvcA=="

    # CORS
    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://localhost:5174,"
        "https://causium-api-2026-fea3frguggasbcg3.brazilsouth-01.azurewebsites.net,"
        "https://gentle-sea-0b9925a0f.7.azurestaticapps.net"
    )

    # SP-A04: Origin / Referer validation on auth state-mutation endpoints.
    # Provides defense-in-depth against CSRF for clients that bypass SameSite=Strict.
    # In production, requests without a recognisable Origin/Referer are rejected.
    # In non-production environments they are logged and allowed through, so that
    # automated API tests (which send no browser headers) continue to work.
    origin_validation_enabled: bool = True

    # Security hardening
    security_headers_enabled: bool = True

    # Production CSP — strict; no external scripts/styles; upgrade-insecure-requests
    # forces HTTPS for all subresource loads. Can be overridden via CSP_POLICY in .env.
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

    # Landing page CSP — allows the external CDNs used by the public marketing page.
    # Applied only to /landing/* routes; the strict production CSP remains in effect
    # for all /api/* and /app/* paths so the authenticated app is not affected.
    csp_policy_landing: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com https://code.iconify.design https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
        "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://storage.googleapis.com; "
        "media-src 'none'; "
        "object-src 'none'; "
        "frame-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests"
    )

    # Dev/local CSP — allows CDN assets required by Swagger UI.
    # upgrade-insecure-requests is intentionally absent: on a plain HTTP
    # dev server it would rewrite http://127.0.0.1/openapi.json to https://
    # causing Swagger UI to fail fetching the schema.
    # Can be overridden via CSP_POLICY_DEV in .env.
    csp_policy_dev: str = (
        "default-src 'self'; "
        # 'unsafe-inline' is required for Swagger UI's inline initialisation script
        # (<script>const ui = SwaggerUIBundle({...})</script>). ReDoc does not need it
        # because it uses a web component (<redoc spec-url=...>) with no inline code.
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
        "font-src 'self'; "
        # Allow Swagger UI to fetch /openapi.json from both loopback aliases
        # a developer might use (127.0.0.1 and localhost are distinct origins).
        "connect-src 'self' http://127.0.0.1:8000 http://localhost:8000 https://storage.googleapis.com; "
        "media-src 'none'; "
        "object-src 'none'; "
        "frame-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    permissions_policy: str = (
        "accelerometer=(), "
        "autoplay=(), "
        "camera=(), "
        "display-capture=(), "
        "encrypted-media=(), "
        "fullscreen=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "keyboard-map=(), "
        "magnetometer=(), "
        "microphone=(), "
        "midi=(), "
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

    # OpenTelemetry (SP-OP06)
    # Set OTEL_EXPORTER_OTLP_ENDPOINT to enable distributed tracing export.
    # When empty the SDK runs in no-op mode (zero overhead).
    otel_service_name: str = "causium-backend"
    otel_exporter_otlp_endpoint: str = ""
    # Sampling ratio: 1.0 = 100%, 0.1 = 10%.  Use parentbased_always_on in
    # dev and a lower ratio (e.g. 0.1) in high-traffic production.
    otel_sample_ratio: float = 1.0

    # AI / PulseIntel
    ai_provider: str = "mock"
    ai_enabled_plans: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 30.0
    ai_openai_api_key: str = ""
    ai_openai_base_url: str = "https://api.openai.com/v1"

    # Workers
    ingestion_worker_enabled: bool = True
    export_worker_enabled: bool = True
    ingestion_interval_hours: int = 6
    scoring_interval_hours: int = 1
    anomaly_detection_interval_minutes: int = 30
    anomaly_detection_lookback_days: int = 14
    anomaly_detection_zscore_threshold: float = 2.5
    anomaly_detection_min_history_days: int = 7
    anomaly_detection_min_delta_usd: float = 10.0
    usage_observation_interval_minutes: int = 30
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
        app_env = self.app_env.strip().lower()
        env_runtime = os.getenv("ENVIRONMENT", "").strip().lower()
        azure_site_name = os.getenv("WEBSITE_SITE_NAME", "").strip()
        if app_env == "production" or env_runtime == "production":
            return True
        # Azure staging mode: allow SQLite fallback when DATABASE_URL is absent.
        if azure_site_name:
            db_url = os.getenv("DATABASE_URL", "").strip()
            # If DATABASE_URL is absent and APP_ENV is staging/dev, use staging mode
            if not db_url and app_env in {"", "development", "dev", "local", "staging"}:
                return False
            # If DATABASE_URL is present but APP_ENV is still dev/local, treat as production
            if app_env in {"", "development", "dev", "local"}:
                return True
        return False

    @property
    def database_url_effective(self) -> str:
        env_db_url = os.getenv("DATABASE_URL", "").strip()
        if env_db_url:
            return env_db_url
        # In Azure App Service, missing DATABASE_URL should trigger the staging
        # fallback instead of silently using any local/default config.
        if os.getenv("WEBSITE_SITE_NAME", "").strip():
            return self.sqlite_fallback_url.strip()
        cfg_db_url = self.database_url.strip()
        if cfg_db_url:
            return cfg_db_url
        return self.sqlite_fallback_url.strip()

    @property
    def redis_url_effective(self) -> str:
        env_redis_url = os.getenv("REDIS_URL", "").strip()
        if env_redis_url:
            return env_redis_url
        # In Azure App Service, missing REDIS_URL keeps Redis disabled (staging mode).
        if os.getenv("WEBSITE_SITE_NAME", "").strip():
            return ""
        return self.redis_url.strip()

    @property
    def redis_enabled(self) -> bool:
        return bool(self.redis_url_effective)

    @property
    def effective_csp_policy(self) -> str:
        """Return the CSP suited for the current environment.

        Production uses the strict policy (csp_policy); every other
        environment uses csp_policy_dev, which allows CDN assets needed by
        Swagger UI and omits upgrade-insecure-requests so that HTTP dev
        servers can serve /openapi.json without being upgraded to HTTPS.
        """
        return self.csp_policy if self.is_production else self.csp_policy_dev

    @property
    def azure_credentials_available(self) -> bool:
        return bool(self.azure_tenant_id and self.azure_client_id and self.azure_client_secret)

    @property
    def aws_credentials_available(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def gcp_credentials_available(self) -> bool:
        if not self.gcp_project_id:
            return False
        return bool(self.gcp_service_account_json or self.gcp_use_workload_identity)

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

    @property
    def auth_cookie_samesite_effective(self) -> str:
        raw = (self.auth_cookie_samesite or "").strip().lower()
        if raw not in {"lax", "strict", "none"}:
            raw = "lax"
        # Browsers reject SameSite=None without Secure.
        if raw == "none" and not self.auth_cookie_secure_effective:
            return "lax"
        return raw

    def validate_production_security(self) -> None:
        if not self.is_production:
            return

        # --- Critical key material checks (unconditional in production) ---
        # These MUST NOT be bypassed by any flag — running production with
        # known default keys is an unacceptable security risk.
        _default_secret = "change-me-in-production-at-least-32-chars"
        if self.secret_key == _default_secret:
            raise RuntimeError(
                "CRITICAL: Refusing to start in production with default SECRET_KEY. "
                "Configure a secure, random value (>=32 chars) via the SECRET_KEY environment variable."
            )
        if len(self.secret_key) < 32:
            raise RuntimeError(
                "CRITICAL: SECRET_KEY must be at least 32 characters in production. "
                "Current length: %d." % len(self.secret_key)
            )

        _default_enc_key = "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItZGV2ZWxvcA=="
        if self.encryption_key == _default_enc_key:
            raise RuntimeError(
                "CRITICAL: Refusing to start in production with default ENCRYPTION_KEY. "
                "Configure a secure Fernet-compatible key via the ENCRYPTION_KEY environment variable."
            )

        if not self.force_secure_datastores_in_production:
            return

        if not self.security_headers_enabled:
            raise ValueError("SECURITY_HEADERS_ENABLED must be true in production")

        # Allow SQLite staging fallback in Azure without external datastores
        db_url_raw = self.database_url_effective.strip()
        db_is_sqlite = db_url_raw.lower().startswith("sqlite+")
        if db_is_sqlite:
            # SQLite staging mode - skip remaining datastore validations
            return
        redis_url_raw = self.redis_url_effective.strip()
        if not db_url_raw:
            raise ValueError(
                "DATABASE_URL is required in production. "
                "Set Azure App Service Application Setting DATABASE_URL="
                "postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB"
            )

        from urllib.parse import urlparse

        db_host = (urlparse(db_url_raw).hostname or "").strip().lower()
        redis_host = (urlparse(redis_url_raw).hostname or "").strip().lower()
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        db_is_sqlite = db_url_raw.lower().startswith("sqlite+")
        if not db_is_sqlite and db_host in local_hosts:
            raise ValueError(
                "DATABASE_URL points to localhost in production. "
                "Use the managed PostgreSQL host in Azure App Service settings."
            )
        if redis_url_raw and redis_host in local_hosts:
            raise ValueError(
                "REDIS_URL points to localhost in production. "
                "Use the managed Redis host in Azure App Service settings."
            )

        db_url = db_url_raw.lower()
        if not db_is_sqlite:
            url_has_sslmode = "sslmode=" in db_url
            url_sslmode_secure = any(
                v in db_url for v in ("sslmode=require", "sslmode=verify-ca", "sslmode=verify-full")
            )
            # Keep validation aligned with explicit SQLAlchemy SSL configuration:
            # create_async_engine(..., connect_args={"ssl": ssl_ctx}) should be
            # considered enabled only when db_ssl_enabled is explicitly true.
            ssl_via_connect_args = self.db_ssl_enabled

            if url_has_sslmode and not url_sslmode_secure:
                raise ValueError("DATABASE_URL sslmode must be require/verify-ca/verify-full in production")
            if not (url_sslmode_secure or ssl_via_connect_args):
                raise ValueError(
                    "PostgreSQL TLS must be enabled in production via DATABASE_URL sslmode "
                    "(require/verify-ca/verify-full) or SQLAlchemy connect_args ssl context"
                )

        if redis_url_raw and not redis_url_raw.lower().startswith("rediss://"):
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

        if redis_url_raw and self.redis_ssl_min_version not in ("TLSv1.2", "TLSv1.3"):
            raise ValueError(
                "REDIS_SSL_MIN_VERSION must be TLSv1.2 or TLSv1.3 in production "
                "(Azure Cache for Redis Basic/Standard supports TLS 1.2)"
            )

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
