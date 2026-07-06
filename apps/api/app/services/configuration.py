from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import cipher
from app.models import Setting


@dataclass(frozen=True)
class NetworkConfiguration:
    method: str
    provider: str
    network: str
    currency: str
    address: str | None
    contract_address: str | None
    decimals: int
    required_confirmations: int
    enabled: bool
    api_key: str | None


@dataclass(frozen=True)
class BinanceConfiguration:
    uid: str | None
    merchant_id: str | None
    api_key: str | None
    api_secret: str | None
    webhook_public_key: str | None
    base_url: str


@dataclass(frozen=True)
class AutomationConfiguration:
    payment_expiry_minutes: int
    verification_max_attempts: int
    manual_review_amount: Decimal
    fraud_score_threshold: int
    reservation_minutes: int
    delivery_max_attempts: int


class ConfigurationService:
    """Reads Admin-managed settings first and uses environment values only as bootstrap defaults."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def payment_network(self, method: str) -> NetworkConfiguration:
        defaults = {
            "usdt_trc20": {
                "provider": "crypto",
                "network": "USDT_TRC20",
                "currency": "USDT",
                "address": settings.payment_usdt_trc20_address,
                "contract_address": settings.payment_usdt_trc20_contract_address,
                "decimals": settings.payment_trc20_decimals,
                "required_confirmations": settings.payment_trc20_confirmations,
                "enabled": settings.payment_trc20_enabled,
                "api_key": settings.tron_grid_api_key,
            },
            "usdt_bep20": {
                "provider": "crypto",
                "network": "USDT_BEP20",
                "currency": "USDT",
                "address": settings.payment_usdt_bep20_address,
                "contract_address": settings.payment_usdt_bep20_contract_address,
                "decimals": settings.payment_bep20_decimals,
                "required_confirmations": settings.payment_bep20_confirmations,
                "enabled": settings.payment_bep20_enabled,
                "api_key": settings.bsc_scan_api_key,
            },
            "binance": {
                "provider": "binance",
                "network": "BINANCE",
                "currency": "USDT",
                "address": None,
                "contract_address": None,
                "decimals": 8,
                "required_confirmations": 1,
                "enabled": settings.payment_binance_enabled,
                "api_key": None,
            },
            "wallet": {
                "provider": "wallet",
                "network": "WALLET",
                "currency": "USD",
                "address": None,
                "contract_address": None,
                "decimals": 2,
                "required_confirmations": 1,
                "enabled": True,
                "api_key": None,
            },
        }
        overrides = await self._value(f"payments.methods.{method}")
        if method in defaults:
            values = {
                **defaults[method],
                **{key: value for key, value in overrides.items() if key in defaults[method]},
            }
        elif overrides:
            values = {
                "provider": overrides.get("provider"),
                "network": overrides.get("network"),
                "currency": overrides.get("currency", "USDT"),
                "address": overrides.get("address"),
                "contract_address": overrides.get("contract_address"),
                "decimals": overrides.get("decimals", 8),
                "required_confirmations": overrides.get("required_confirmations", 1),
                "enabled": overrides.get("enabled", False),
                "api_key": overrides.get("api_key"),
            }
            if not values["provider"] or not values["network"]:
                raise ValueError("payments.provider_configuration_invalid")
        else:
            raise ValueError("payments.unsupported_method")
        return NetworkConfiguration(
            method=method,
            provider=str(values["provider"]),
            network=str(values["network"]),
            currency=str(values["currency"]),
            address=str(values["address"]) if values["address"] else None,
            contract_address=str(values["contract_address"]) if values["contract_address"] else None,
            decimals=int(values["decimals"]),
            required_confirmations=int(values["required_confirmations"]),
            enabled=bool(values["enabled"]),
            api_key=str(values["api_key"]) if values["api_key"] else None,
        )

    async def automation(self) -> AutomationConfiguration:
        values = await self._value("automation.payment")
        return AutomationConfiguration(
            payment_expiry_minutes=int(values.get("payment_expiry_minutes", settings.payment_expiry_minutes)),
            verification_max_attempts=int(values.get("verification_max_attempts", settings.payment_verification_max_attempts)),
            manual_review_amount=Decimal(str(values.get("manual_review_amount", settings.payment_manual_review_amount))),
            fraud_score_threshold=int(values.get("fraud_score_threshold", settings.payment_fraud_score_threshold)),
            reservation_minutes=int(values.get("reservation_minutes", settings.inventory_reservation_minutes)),
            delivery_max_attempts=int(values.get("delivery_max_attempts", settings.delivery_max_attempts)),
        )

    async def delivery_provider(self, provider_key: str) -> dict[str, Any]:
        return await self._value(f"delivery.providers.{provider_key}")

    async def binance(self) -> BinanceConfiguration:
        values = await self._value("payments.providers.binance")
        return BinanceConfiguration(
            uid=values.get("uid", settings.binance_uid),
            merchant_id=values.get("merchant_id", settings.binance_merchant_id),
            api_key=values.get("api_key", settings.binance_api_key),
            api_secret=values.get("api_secret", settings.binance_api_secret),
            webhook_public_key=values.get("webhook_public_key", settings.binance_webhook_public_key),
            base_url=str(values.get("base_url", settings.binance_pay_base_url)),
        )

    async def _value(self, key: str) -> dict[str, Any]:
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if not setting or not isinstance(setting.value, dict):
            return {}
        if setting.is_secret and isinstance(setting.value.get("ciphertext"), str):
            decrypted = json.loads(cipher.decrypt(setting.value["ciphertext"]))
            return dict(decrypted) if isinstance(decrypted, dict) else {}
        return dict(setting.value)
