from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class InventoryPoolCreate(APIModel):
    product_variant_id: UUID
    name: str = Field(min_length=2, max_length=160)
    delivery_type: str = Field(min_length=2, max_length=48)
    provider_key: str | None = Field(default=None, max_length=120)
    priority: int = Field(default=100, ge=0, le=10000)
    unlimited_stock: bool = False
    low_stock_threshold: int = Field(default=5, ge=0, le=1000000)


class InventoryAssetUpload(APIModel):
    payloads: list[str] = Field(min_length=1, max_length=5000)
    metadata: dict = Field(default_factory=dict)


class InventoryAdjustment(APIModel):
    quantity_available: int = Field(ge=0, le=10000000)
    unlimited_stock: bool = False
    low_stock_threshold: int = Field(default=5, ge=0, le=1000000)


class ManualPaymentApproval(APIModel):
    reference: str = Field(min_length=6, max_length=255)
    confirmed_amount: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class ManualPaymentRejection(APIModel):
    reason: str = Field(min_length=3, max_length=255)
