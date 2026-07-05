from __future__ import annotations

from functools import cached_property
import json
import sys

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr = Field(alias="BOT_TOKEN")
    bot_mode: str = Field(default="webhook", alias="BOT_MODE")
    webhook_base_url: str | None = Field(default=None, alias="WEBHOOK_BASE_URL")
    webhook_path: str = Field(default="/telegram/webhook", alias="WEBHOOK_PATH")
    webhook_secret: SecretStr | None = Field(default=None, alias="WEBHOOK_SECRET")
    web_server_host: str = Field(default="0.0.0.0", alias="WEB_SERVER_HOST")
    web_server_port: int = Field(default=8080, alias="WEB_SERVER_PORT")

    api_base_url: str = Field(alias="API_BASE_URL")
    api_service_key: SecretStr | None = Field(default=None, alias="TELEGRAM_SERVICE_API_KEY")
    api_timeout_seconds: float = Field(default=8, alias="API_TIMEOUT_SECONDS")
    api_retries: int = Field(default=2, alias="API_RETRIES")

    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    default_locale: str = Field(default="en", alias="DEFAULT_LOCALE")
    bot_public_username: str = Field(alias="BOT_PUBLIC_USERNAME")
    admin_telegram_id: int | None = Field(default=None, alias="TELEGRAM_ADMIN_ID")
    throttle_limit: int = Field(default=12, alias="THROTTLE_LIMIT")
    throttle_window_seconds: int = Field(default=5, alias="THROTTLE_WINDOW_SECONDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("bot_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in {"webhook", "polling"}:
            raise ValueError("BOT_MODE must be webhook or polling")
        return value

    @field_validator("bot_public_username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.removeprefix("@").strip()
        if not normalized:
            raise ValueError("BOT_PUBLIC_USERNAME is required")
        return normalized

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.bot_mode != "webhook":
            return self
        if not self.webhook_base_url or not self.webhook_base_url.startswith("https://"):
            raise ValueError("WEBHOOK_BASE_URL must use HTTPS in webhook mode")
        if not self.webhook_secret or len(self.webhook_secret.get_secret_value()) < 32:
            raise ValueError("WEBHOOK_SECRET must contain at least 32 characters in webhook mode")
        if not self.redis_url:
            raise ValueError("REDIS_URL is required in webhook mode")
        if not self.bot_public_username:
            raise ValueError("BOT_PUBLIC_USERNAME is required in webhook mode")
        if self.admin_telegram_id is None:
            raise ValueError("TELEGRAM_ADMIN_ID is required in webhook mode")
        if not self.api_service_key or len(self.api_service_key.get_secret_value()) < 32:
            raise ValueError("API_SERVICE_KEY must contain at least 32 characters in webhook mode")
        return self

    @property
    def bot_token_value(self) -> str:
        return self.bot_token.get_secret_value()

    @property
    def webhook_secret_value(self) -> str | None:
        return self.webhook_secret.get_secret_value() if self.webhook_secret else None

    @property
    def api_service_key_value(self) -> str | None:
        return self.api_service_key.get_secret_value() if self.api_service_key else None

    @cached_property
    def webhook_url(self) -> str | None:
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"


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
