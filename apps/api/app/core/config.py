from __future__ import annotations

from functools import cached_property
import base64
import json
import sys

from pydantic import Field, HttpUrl, SecretStr, ValidationError, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RavenStore API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    expose_api_docs: bool = False
    backend_cors_origins_raw: str = Field(default="", alias="BACKEND_CORS_ORIGINS")
    trusted_proxy_cidrs_raw: str = Field(default="", alias="TRUSTED_PROXY_CIDRS")
    sensitive_service_allowlist_raw: str = Field(default="", alias="SENSITIVE_SERVICE_ALLOWLIST")
    api_public_url: str | None = None
    admin_public_url: str | None = None
    storefront_public_url: str | None = None

    database_url: str = Field(alias="DATABASE_URL")
    database_direct_url: str | None = Field(default=None, alias="DATABASE_DIRECT_URL")
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout_seconds: int = 30
    database_pool_recycle_seconds: int = 1800
    supabase_project_ref: str | None = None
    supabase_project_url: HttpUrl | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_database_password: SecretStr | None = None
    supabase_product_files_bucket: str = "product-files"
    supabase_product_images_bucket: str = "product-images"
    supabase_backups_bucket: str = "backups"
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    event_stream_name: str = "ravenstore:events:v1"
    event_stream_max_length: int = 100000
    event_worker_max_attempts: int = 12
    event_outbox_retention_days: int = 30
    event_sse_heartbeat_seconds: int = 15
    cache_default_ttl_seconds: int = 60
    cache_prefix: str = "ravenstore:cache:v1"

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_refresh_secret_key: str = Field(alias="JWT_REFRESH_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    jwt_issuer: str = "ravenstore-api"
    jwt_audience: str = "ravenstore-clients"
    login_max_attempts: int = 8
    login_attempt_window_seconds: int = 900
    account_lockout_seconds: int = 1800

    encryption_key: str = Field(alias="ENCRYPTION_KEY")
    api_key_pepper: str = Field(alias="API_KEY_PEPPER")

    payment_usdt_trc20_address: str | None = None
    payment_usdt_bep20_address: str | None = None
    payment_usdt_trc20_contract_address: str | None = None
    payment_usdt_bep20_contract_address: str | None = None
    payment_trc20_confirmations: int = 20
    payment_bep20_confirmations: int = 15
    payment_trc20_decimals: int = 6
    payment_bep20_decimals: int = 18
    payment_expiry_minutes: int = 45
    payment_verification_max_attempts: int = 12
    payment_manual_review_amount: float = 1000
    payment_fraud_score_threshold: int = 70
    payment_trc20_enabled: bool = True
    payment_bep20_enabled: bool = True
    payment_binance_enabled: bool = False
    binance_uid: str | None = None
    binance_merchant_id: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None
    binance_webhook_public_key: str | None = None
    binance_pay_base_url: str = "https://bpay.binanceapi.com"
    tron_grid_api_key: str | None = None
    bsc_scan_api_key: str | None = None
    inventory_reservation_minutes: int = 60
    delivery_max_attempts: int = 8

    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_bot_username: str | None = None
    telegram_admin_id: int | None = None
    telegram_service_api_key: SecretStr | None = None
    initial_owner_email: str | None = None
    initial_owner_password: SecretStr | None = None

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    backup_dir: str = "./backups"
    backup_enabled: bool = True
    backup_retention_days: int = 30
    backup_interval_hours: int = 24
    backup_encryption_key: str | None = None
    upload_quarantine_dir: str = "./uploads/quarantine"
    uploads_enabled: bool = True
    upload_max_bytes: int = 25 * 1024 * 1024
    upload_allowed_types_raw: str = "application/pdf,application/zip"
    upload_require_antivirus: bool = True
    clamav_host: str | None = None
    clamav_port: int = 3310
    metrics_bearer_token: str | None = None
    worker_heartbeat_ttl_seconds: int = 45
    external_http_timeout_seconds: float = 20.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_seconds: int = 30
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "ravenstore-api"
    log_level: str = "INFO"

    @field_validator("jwt_secret_key", "jwt_refresh_secret_key", "api_key_pepper")
    @classmethod
    def enforce_secret_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("secret values must be at least 32 characters")
        return value

    @field_validator("encryption_key", "backup_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None or (value == "" and info.field_name == "backup_encryption_key"):
            return None
        try:
            decoded = base64.urlsafe_b64decode(value.encode())
        except Exception as exc:
            raise ValueError("encryption keys must be URL-safe base64") from exc
        if len(decoded) != 32:
            raise ValueError("encryption keys must decode to 32 bytes")
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if not self.backend_cors_origins:
            raise ValueError("BACKEND_CORS_ORIGINS is required in production")
        if any(origin == "*" or origin.startswith("http://") for origin in self.backend_cors_origins):
            raise ValueError("production CORS origins must be explicit HTTPS origins")
        if self.jwt_secret_key == self.jwt_refresh_secret_key:
            raise ValueError("access and refresh JWT secrets must be different")
        if not self.redis_url:
            raise ValueError("REDIS_URL is required in production")
        if not self.upload_require_antivirus or not self.clamav_host:
            raise ValueError("production uploads require UPLOAD_REQUIRE_ANTIVIRUS=true and CLAMAV_HOST")
        required = {
            "API_PUBLIC_URL": self.api_public_url,
            "ADMIN_PUBLIC_URL": self.admin_public_url,
            "STOREFRONT_PUBLIC_URL": self.storefront_public_url,
            "SUPABASE_PROJECT_REF": self.supabase_project_ref,
            "SUPABASE_PROJECT_URL": self.supabase_project_url,
            "SUPABASE_ANON_KEY": self.supabase_anon_key,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_BOT_USERNAME": self.telegram_bot_username,
            "TELEGRAM_ADMIN_ID": self.telegram_admin_id,
            "TELEGRAM_SERVICE_API_KEY": self.telegram_service_api_key,
            "METRICS_BEARER_TOKEN": self.metrics_bearer_token,
        }
        missing = [name for name, value in required.items() if value in (None, "")]
        if missing:
            raise ValueError(f"missing production variables: {', '.join(missing)}")
        if self.payment_trc20_enabled:
            self._require_payment_values(
                "TRC20",
                {
                    "PAYMENT_USDT_TRC20_ADDRESS": self.payment_usdt_trc20_address,
                    "PAYMENT_USDT_TRC20_CONTRACT_ADDRESS": self.payment_usdt_trc20_contract_address,
                    "TRON_GRID_API_KEY": self.tron_grid_api_key,
                },
            )
        if self.payment_bep20_enabled:
            self._require_payment_values(
                "BEP20",
                {
                    "PAYMENT_USDT_BEP20_ADDRESS": self.payment_usdt_bep20_address,
                    "PAYMENT_USDT_BEP20_CONTRACT_ADDRESS": self.payment_usdt_bep20_contract_address,
                    "BSC_SCAN_API_KEY": self.bsc_scan_api_key,
                },
            )
        if self.payment_binance_enabled:
            self._require_payment_values(
                "Binance Pay",
                {
                    "BINANCE_UID": self.binance_uid,
                    "BINANCE_MERCHANT_ID": self.binance_merchant_id,
                    "BINANCE_API_KEY": self.binance_api_key,
                    "BINANCE_API_SECRET": self.binance_api_secret,
                    "BINANCE_WEBHOOK_PUBLIC_KEY": self.binance_webhook_public_key,
                },
            )
        return self

    @model_validator(mode="after")
    def validate_initial_owner(self) -> "Settings":
        if bool(self.initial_owner_email) != bool(self.initial_owner_password):
            raise ValueError("INITIAL_OWNER_EMAIL and INITIAL_OWNER_PASSWORD must be provided together")
        if self.initial_owner_password and len(self.initial_owner_password.get_secret_value()) < 16:
            raise ValueError("INITIAL_OWNER_PASSWORD must contain at least 16 characters")
        return self

    @field_validator("database_url", "database_direct_url")
    @classmethod
    def validate_database_urls(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database URLs must use postgresql+asyncpg://")
        return value

    @field_validator("supabase_project_ref")
    @classmethod
    def validate_project_ref(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 20 or not value.isalnum()):
            raise ValueError("SUPABASE_PROJECT_REF must be the 20-character project reference")
        return value

    @field_validator("telegram_bot_username")
    @classmethod
    def normalize_bot_username(cls, value: str | None) -> str | None:
        return value.removeprefix("@").strip() if value else value

    def _require_payment_values(self, provider: str, values: dict[str, object]) -> None:
        missing = [name for name, value in values.items() if value in (None, "")]
        if missing:
            raise ValueError(f"{provider} is enabled but missing: {', '.join(missing)}")

    @cached_property
    def backend_cors_origins(self) -> list[str]:
        if not self.backend_cors_origins_raw:
            return []
        return [origin.strip() for origin in self.backend_cors_origins_raw.split(",") if origin.strip()]

    @cached_property
    def trusted_proxy_cidrs(self) -> list[str]:
        return [value.strip() for value in self.trusted_proxy_cidrs_raw.split(",") if value.strip()]

    @cached_property
    def sensitive_service_allowlist(self) -> list[str]:
        return [value.strip() for value in self.sensitive_service_allowlist_raw.split(",") if value.strip()]

    @cached_property
    def upload_allowed_types(self) -> set[str]:
        return {value.strip().lower() for value in self.upload_allowed_types_raw.split(",") if value.strip()}

    @cached_property
    def api_docs_enabled(self) -> bool:
        return self.environment.lower() != "production" or self.expose_api_docs

    @property
    def migration_database_url(self) -> str:
        return self.database_direct_url or self.database_url


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        failures = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors(include_input=False, include_url=False)
        ]
        print(json.dumps({"event": "configuration.invalid", "errors": failures}), file=sys.stderr)
        raise SystemExit(78) from None


settings = load_settings()
