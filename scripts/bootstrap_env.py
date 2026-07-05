from __future__ import annotations

import base64
import getpass
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def secret(name: str, prompt: str) -> str:
    value = os.getenv(name) or getpass.getpass(f"{prompt}: ").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def public(name: str, prompt: str, default: str = "") -> str:
    value = os.getenv(name) or input(f"{prompt}{f' [{default}]' if default else ''}: ").strip() or default
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def generated_urlsafe(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def fernet_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def write_env(path: Path, values: dict[str, str | int | bool]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={str(value).lower() if isinstance(value, bool) else value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def main() -> None:
    project_ref = public("SUPABASE_PROJECT_REF", "Supabase project reference")
    project_url = public("SUPABASE_PROJECT_URL", "Supabase project URL", f"https://{project_ref}.supabase.co")
    anon_key = secret("SUPABASE_ANON_KEY", "Supabase anon key")
    service_key = secret("SUPABASE_SERVICE_ROLE_KEY", "Supabase service-role key")
    database_password = secret("SUPABASE_DATABASE_PASSWORD", "Supabase database password")
    database_url = secret("DATABASE_URL", "Supabase session-pooler SQLAlchemy URL")
    direct_url = os.getenv("DATABASE_DIRECT_URL", "").strip()

    bot_token = secret("TELEGRAM_BOT_TOKEN", "Telegram bot token")
    bot_username = public("TELEGRAM_BOT_USERNAME", "Telegram bot username").removeprefix("@")
    admin_id = public("TELEGRAM_ADMIN_ID", "Numeric Telegram admin ID")
    trc20_address = public("PAYMENT_USDT_TRC20_ADDRESS", "USDT TRC20 receiving address")
    bep20_address = public("PAYMENT_USDT_BEP20_ADDRESS", "USDT BEP20 receiving address")
    binance_uid = public("BINANCE_UID", "Binance UID")
    owner_email = public("INITIAL_OWNER_EMAIL", "Initial RavenStore Owner email")
    owner_password = secret("INITIAL_OWNER_PASSWORD", "Initial RavenStore Owner password (16+ characters)")
    if len(owner_password) < 16:
        raise SystemExit("INITIAL_OWNER_PASSWORD must contain at least 16 characters")

    api_service_key = generated_urlsafe()
    api_values = {
        "ENVIRONMENT": "development",
        "API_PUBLIC_URL": "http://localhost:8000",
        "ADMIN_PUBLIC_URL": "http://localhost:3000",
        "STOREFRONT_PUBLIC_URL": "http://localhost:3001",
        "BACKEND_CORS_ORIGINS": "http://localhost:3000,http://localhost:3001",
        "TRUSTED_PROXY_CIDRS": "127.0.0.1/32,::1/128",
        "SENSITIVE_SERVICE_ALLOWLIST": "127.0.0.1/32,::1/128",
        "SUPABASE_PROJECT_REF": project_ref,
        "SUPABASE_PROJECT_URL": project_url,
        "SUPABASE_ANON_KEY": anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": service_key,
        "SUPABASE_DATABASE_PASSWORD": database_password,
        "DATABASE_URL": database_url,
        "DATABASE_DIRECT_URL": direct_url,
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "JWT_SECRET_KEY": generated_urlsafe(64),
        "JWT_REFRESH_SECRET_KEY": generated_urlsafe(64),
        "ENCRYPTION_KEY": fernet_key(),
        "API_KEY_PEPPER": generated_urlsafe(64),
        "METRICS_BEARER_TOKEN": generated_urlsafe(48),
        "BACKUP_ENCRYPTION_KEY": fernet_key(),
        "TELEGRAM_BOT_TOKEN": bot_token,
        "TELEGRAM_BOT_USERNAME": bot_username,
        "TELEGRAM_ADMIN_ID": admin_id,
        "TELEGRAM_WEBHOOK_SECRET": generated_urlsafe(32),
        "TELEGRAM_SERVICE_API_KEY": api_service_key,
        "INITIAL_OWNER_EMAIL": owner_email,
        "INITIAL_OWNER_PASSWORD": owner_password,
        "PAYMENT_USDT_TRC20_ADDRESS": trc20_address,
        "PAYMENT_USDT_BEP20_ADDRESS": bep20_address,
        "BINANCE_UID": binance_uid,
        "PAYMENT_BINANCE_ENABLED": False,
        "PAYMENT_TRC20_ENABLED": False,
        "PAYMENT_BEP20_ENABLED": False,
        "UPLOADS_ENABLED": False,
        "BACKUP_ENABLED": False,
    }
    write_env(ROOT / "apps/api/.env", api_values)
    write_env(
        ROOT / "apps/bot/.env",
        {
            "BOT_TOKEN": bot_token,
            "BOT_MODE": "polling",
            "BOT_PUBLIC_USERNAME": bot_username,
            "TELEGRAM_ADMIN_ID": admin_id,
            "API_BASE_URL": "http://localhost:8000/api/v1",
            "TELEGRAM_SERVICE_API_KEY": api_service_key,
            "REDIS_URL": os.getenv("BOT_REDIS_URL", "redis://localhost:6379/1"),
        },
    )
    write_env(
        ROOT / "apps/web/.env.local",
        {
            "NEXT_PUBLIC_API_BASE_URL": "http://localhost:8000/api/v1",
            "NEXT_PUBLIC_ADMIN_SITE_URL": "http://localhost:3000",
        },
    )
    write_env(
        ROOT / "apps/storefront/.env.local",
        {
            "NEXT_PUBLIC_API_BASE_URL": "http://localhost:8000/api/v1",
            "NEXT_PUBLIC_TELEGRAM_BOT_URL": f"https://t.me/{bot_username}",
            "NEXT_PUBLIC_SITE_URL": "http://localhost:3001",
            "RAVENSTORE_IMAGE_HOST": f"{project_ref}.supabase.co",
        },
    )
    print("Created ignored local environment files. Payment, uploads, and backups remain disabled until provider keys and ClamAV are configured.")


if __name__ == "__main__":
    main()
