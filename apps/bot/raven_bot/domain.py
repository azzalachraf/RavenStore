from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class TelegramIdentity(APIModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    referral_code: str | None = None


class BotSession(APIModel):
    access_token: str | None = None
    locale: str = "en"
    user_id: UUID | None = None
    referral_code: str | None = None
    notifications_enabled: bool = True


class Category(APIModel):
    id: UUID
    slug: str
    name_key: str
    description_key: str | None = None
    sort_order: int = 0
    is_active: bool = True


class ProductImage(APIModel):
    url: str
    alt_key: str | None = None


class ProductVariant(APIModel):
    id: UUID
    sku: str
    name_key: str
    duration_days: int | None = None
    region: str | None = None
    delivery_type: str
    price_amount: Decimal
    cost_amount: Decimal = Decimal("0")
    currency: str = "USD"
    is_active: bool = True
    stock_available: int | None = None
    unlimited_stock: bool = False


class Product(APIModel):
    id: UUID
    category_id: UUID
    slug: str
    name_key: str
    description_key: str | None = None
    status: str
    brand: str | None = None
    product_metadata: dict[str, Any] = Field(default_factory=dict)
    variants: list[ProductVariant] = Field(default_factory=list)
    images: list[ProductImage] = Field(default_factory=list)


class OrderItem(APIModel):
    id: UUID
    product_id: UUID
    product_variant_id: UUID
    quantity: int
    unit_price_amount: Decimal
    snapshot: dict[str, Any] = Field(default_factory=dict)


class Order(APIModel):
    id: UUID
    order_number: str
    status: str
    total_amount: Decimal
    currency: str = "USD"
    created_at: str | None = None
    items: list[OrderItem] = Field(default_factory=list)


class Payment(APIModel):
    id: UUID
    order_id: UUID
    provider: str
    network: str
    status: str
    amount: Decimal
    currency: str
    payment_address: str | None = None
    expires_at: str


class PaymentCreated(APIModel):
    payment: Payment
    payment_token: str
    message_key: str = "payments.verification_queued"


class ReferralStats(APIModel):
    code: str | None = None
    link: str | None = None
    invited_count: int = 0
    reward_amount: Decimal = Decimal("0")
    invited_users: list[dict[str, Any]] = Field(default_factory=list)


class WalletSummary(APIModel):
    purchase_count: int = 0
    future_balance: Decimal = Decimal("0")
    currency: str = "USD"


class SupportTicket(APIModel):
    id: UUID
    subject_key: str
    status: str
    priority: str
