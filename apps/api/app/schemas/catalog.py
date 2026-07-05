from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, JsonDict, TimestampedOut


class CategoryOut(TimestampedOut):
    parent_id: UUID | None
    slug: str
    name_key: str
    description_key: str | None
    sort_order: int
    is_active: bool


class CategoryCreate(APIModel):
    parent_id: UUID | None = None
    slug: str = Field(min_length=2, max_length=160)
    name_key: str
    description_key: str | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(APIModel):
    parent_id: UUID | None = None
    slug: str | None = Field(default=None, min_length=2, max_length=160)
    name_key: str | None = None
    description_key: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ProductImageOut(TimestampedOut):
    product_id: UUID
    url: str
    alt_key: str | None
    sort_order: int


class ProductVariantOut(TimestampedOut):
    product_id: UUID
    sku: str
    name_key: str
    duration_days: int | None
    region: str | None
    delivery_type: str
    price_amount: Decimal
    cost_amount: Decimal
    currency: str
    is_active: bool
    stock_available: int | None = None
    unlimited_stock: bool = False


class ProductOut(TimestampedOut):
    category_id: UUID
    slug: str
    name_key: str
    description_key: str | None
    status: str
    brand: str | None
    product_metadata: JsonDict
    variants: list[ProductVariantOut] = []
    images: list[ProductImageOut] = []


class ProductCreate(APIModel):
    category_id: UUID
    slug: str = Field(min_length=2, max_length=180)
    name_key: str
    description_key: str | None = None
    status: str = "draft"
    brand: str | None = None
    product_metadata: JsonDict = {}


class ProductUpdate(APIModel):
    expected_updated_at: datetime | None = None
    category_id: UUID | None = None
    slug: str | None = Field(default=None, min_length=2, max_length=180)
    name_key: str | None = None
    description_key: str | None = None
    status: str | None = None
    brand: str | None = None
    product_metadata: JsonDict | None = None


class ProductVariantCreate(APIModel):
    product_id: UUID
    sku: str
    name_key: str
    duration_days: int | None = None
    region: str | None = None
    delivery_type: str
    price_amount: Decimal
    cost_amount: Decimal = Decimal("0")
    currency: str = "USD"
    is_active: bool = True


class ProductVariantUpdate(APIModel):
    name_key: str | None = None
    duration_days: int | None = None
    region: str | None = None
    delivery_type: str | None = None
    price_amount: Decimal | None = Field(default=None, ge=0)
    cost_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
