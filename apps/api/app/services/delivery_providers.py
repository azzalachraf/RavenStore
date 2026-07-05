from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.models import InventoryAsset, InventoryReservation, OrderItem, ProductDownload
from app.services.configuration import ConfigurationService
from app.integrations.supabase_storage import SupabaseStorageClient


@dataclass(frozen=True)
class DeliveryContext:
    item: OrderItem
    reservation: InventoryReservation | None
    provider_key: str | None


class DeliveryProvider(Protocol):
    async def deliver(self, context: DeliveryContext) -> str: ...


class InventoryAssetProvider:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def deliver(self, context: DeliveryContext) -> str:
        if context.reservation is None or context.reservation.asset_id is None:
            raise ValueError("delivery.inventory_asset_missing")
        asset = await self.session.get(InventoryAsset, context.reservation.asset_id, with_for_update=True)
        if asset is None or asset.status not in {"reserved", "delivered"}:
            raise ValueError("delivery.inventory_asset_unavailable")
        return cipher.decrypt(asset.payload_encrypted)


class DownloadProvider:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def deliver(self, context: DeliveryContext) -> str:
        download = await self.session.scalar(
            select(ProductDownload)
            .where(ProductDownload.product_variant_id == context.item.product_variant_id)
            .order_by(ProductDownload.created_at)
            .limit(1)
        )
        if download is None:
            raise ValueError("delivery.download_missing")
        storage_reference = cipher.decrypt(download.storage_url_encrypted)
        if storage_reference.startswith("supabase://"):
            return await SupabaseStorageClient().create_signed_url(storage_reference, expires_in=900)
        return storage_reference


class APIGeneratedProvider:
    def __init__(self, session: AsyncSession):
        self.configuration = ConfigurationService(session)

    async def deliver(self, context: DeliveryContext) -> str:
        if not context.provider_key:
            raise ValueError("delivery.provider_not_configured")
        config = await self.configuration.delivery_provider(context.provider_key)
        endpoint = config.get("endpoint")
        if not endpoint or not str(endpoint).startswith("https://"):
            raise ValueError("delivery.provider_endpoint_invalid")
        headers = {"Idempotency-Key": str(context.item.id), "Accept": "application/json"}
        if config.get("authorization"):
            headers["Authorization"] = str(config["authorization"])
        async with httpx.AsyncClient(timeout=float(config.get("timeout_seconds", 20))) as client:
            response = await client.post(
                str(endpoint),
                headers=headers,
                json={
                    "order_item_id": str(context.item.id),
                    "order_id": str(context.item.order_id),
                    "product_variant_id": str(context.item.product_variant_id),
                    "quantity": context.item.quantity,
                },
            )
            response.raise_for_status()
            payload = response.json()
        value = payload.get("delivery") or payload.get("value") or payload.get("url")
        if not isinstance(value, str) or not value:
            raise ValueError("delivery.provider_response_invalid")
        return value


class DeliveryProviderRegistry:
    def __init__(self, session: AsyncSession):
        self.inventory = InventoryAssetProvider(session)
        self.download = DownloadProvider(session)
        self.generated = APIGeneratedProvider(session)

    def resolve(self, *, delivery_type: str, provider_key: str | None) -> DeliveryProvider:
        if provider_key:
            return self.generated
        if delivery_type in {"account", "credentials", "invite_link", "license_key", "activation_code"}:
            return self.inventory
        if delivery_type in {"zip_file", "pdf_file"}:
            return self.download
        if delivery_type == "api_generated":
            return self.generated
        raise ValueError("delivery.type_not_supported")
