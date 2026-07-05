from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, JsonDict, TimestampedOut


class OrderItemCreate(APIModel):
    product_variant_id: UUID
    quantity: int = Field(ge=1, le=100)


class OrderCreate(APIModel):
    items: list[OrderItemCreate] = Field(min_length=1)
    coupon_code: str | None = None


class OrderItemOut(TimestampedOut):
    order_id: UUID
    product_id: UUID
    product_variant_id: UUID
    quantity: int
    unit_price_amount: Decimal
    snapshot: JsonDict


class OrderOut(TimestampedOut):
    order_number: str
    user_id: UUID
    status: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    coupon_id: UUID | None
    items: list[OrderItemOut] = []
