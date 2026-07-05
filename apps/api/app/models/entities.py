from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

JsonDict = dict[str, Any]

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(TimestampedUUIDMixin, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, lazy="selectin")


class Permission(TimestampedUUIDMixin, Base):
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class User(TimestampedUUIDMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    referral_code: Mapped[str] = mapped_column(
        String(64), default=lambda: f"rvn_{uuid4().hex}", unique=True, index=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(160))
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True, nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[Role] = relationship(lazy="selectin")


class TelegramUser(TimestampedUUIDMixin, Base):
    __tablename__ = "telegram_users"
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(128))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(8))
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class AdminProfile(TimestampedUUIDMixin, Base):
    __tablename__ = "admin_profiles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    mfa_recovery_codes_encrypted: Mapped[str | None] = mapped_column(Text)
    mfa_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_admin_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(TimestampedUUIDMixin, Base):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    token_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    session_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))


class Category(TimestampedUUIDMixin, Base):
    __tablename__ = "categories"
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    description_key: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)


class Product(TimestampedUUIDMixin, Base):
    __tablename__ = "products"
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    description_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120))
    product_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", lazy="selectin")
    images: Mapped[list["ProductImage"]] = relationship(lazy="selectin")


class ProductVariant(TimestampedUUIDMixin, Base):
    __tablename__ = "product_variants"
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[str | None] = mapped_column(String(64))
    delivery_type: Mapped[str] = mapped_column(String(48), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    product: Mapped[Product] = relationship(back_populates="variants", lazy="selectin")
    inventory: Mapped["Inventory | None"] = relationship(lazy="selectin", uselist=False)

    @property
    def stock_available(self) -> int | None:
        return self.inventory.quantity_available if self.inventory and not self.inventory.unlimited_stock else None

    @property
    def unlimited_stock(self) -> bool:
        return bool(self.inventory and self.inventory.unlimited_stock)


class ProductImage(TimestampedUUIDMixin, Base):
    __tablename__ = "product_images"
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    alt_key: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ProductDownload(TimestampedUUIDMixin, Base):
    __tablename__ = "product_downloads"
    product_variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_url_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)


class Inventory(TimestampedUUIDMixin, Base):
    __tablename__ = "inventory"
    product_variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), unique=True, nullable=False)
    quantity_available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    unlimited_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LicenseKey(TimestampedUUIDMixin, Base):
    __tablename__ = "license_keys"
    product_variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False)
    key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="available", nullable=False)
    reserved_order_id: Mapped[UUID | None] = mapped_column()
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StockHistory(TimestampedUUIDMixin, Base):
    __tablename__ = "stock_history"
    inventory_id: Mapped[UUID] = mapped_column(ForeignKey("inventory.id", ondelete="CASCADE"), index=True, nullable=False)
    change: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Coupon(TimestampedUUIDMixin, Base):
    __tablename__ = "coupons"
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Referral(TimestampedUUIDMixin, Base):
    __tablename__ = "referrals"
    referrer_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    referred_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    reward_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)


class Order(TimestampedUUIDMixin, Base):
    __tablename__ = "orders"
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending_payment", nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    coupon_id: Mapped[UUID | None] = mapped_column(ForeignKey("coupons.id", ondelete="SET NULL"))
    items: Mapped[list["OrderItem"]] = relationship(lazy="selectin")


class OrderItem(TimestampedUUIDMixin, Base):
    __tablename__ = "order_items"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    snapshot: Mapped[JsonDict] = mapped_column(JSONB, nullable=False)


class Payment(TimestampedUUIDMixin, Base):
    __tablename__ = "payments"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    payment_address: Mapped[str | None] = mapped_column(String(255))
    payment_reference_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    payment_reference_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payment_token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    provider_order_id_encrypted: Mapped[str | None] = mapped_column(Text)
    payment_url: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_review_reason: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Transaction(TimestampedUUIDMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("network", "tx_hash", name="uq_transactions_network_hash"),)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_payload: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)


class PaymentVerification(TimestampedUUIDMixin, Base):
    __tablename__ = "payment_verifications"
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True, unique=True, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    submitted_tx_hash: Mapped[str | None] = mapped_column(String(255))
    submitted_reference_encrypted: Mapped[str | None] = mapped_column(Text)
    submitted_reference_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(120))
    last_error: Mapped[str | None] = mapped_column(Text)


class DeliveryQueue(TimestampedUUIDMixin, Base):
    __tablename__ = "delivery_queue"
    __table_args__ = (UniqueConstraint("order_item_id", name="uq_delivery_queue_order_item"),)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    order_item_id: Mapped[UUID] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued", nullable=False)
    payload_encrypted: Mapped[str | None] = mapped_column(Text)
    provider_key: Mapped[str | None] = mapped_column(String(120))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class DeliveryLog(TimestampedUUIDMixin, Base):
    __tablename__ = "delivery_logs"
    delivery_id: Mapped[UUID] = mapped_column(ForeignKey("delivery_queue.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message_key: Mapped[str] = mapped_column(String(255), nullable=False)
    log_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class Notification(TimestampedUUIDMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("source_event_id", "user_id", "channel", name="uq_notification_event_user_channel"),
    )
    source_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("outbox_events.id", ondelete="SET NULL"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    title_key: Mapped[str] = mapped_column(String(255), nullable=False)
    body_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True, nullable=False)
    payload: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Setting(TimestampedUUIDMixin, Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    value: Mapped[JsonDict] = mapped_column(JSONB, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Language(TimestampedUUIDMixin, Base):
    __tablename__ = "languages"
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_rtl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TranslationKey(TimestampedUUIDMixin, Base):
    __tablename__ = "translation_keys"
    __table_args__ = (UniqueConstraint("key", "language_code", name="uq_translation_key_language"),)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class AnalyticsEvent(TimestampedUUIDMixin, Base):
    __tablename__ = "analytics_events"
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    event_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class AnalyticsDailyMetric(TimestampedUUIDMixin, Base):
    __tablename__ = "analytics_daily_metrics"
    __table_args__ = (UniqueConstraint("metric_date", "metric_key", name="uq_metric_date_key"),)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    metric_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class ActivityLog(TimestampedUUIDMixin, Base):
    __tablename__ = "activity_logs"
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column()
    activity_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class SecurityEvent(TimestampedUUIDMixin, Base):
    __tablename__ = "security_events"
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    trace_id: Mapped[str | None] = mapped_column(String(120), index=True)
    event_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupportTicket(TimestampedUUIDMixin, Base):
    __tablename__ = "support_tickets"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    assigned_to_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class SupportMessage(TimestampedUUIDMixin, Base):
    __tablename__ = "support_messages"
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body_encrypted: Mapped[str] = mapped_column(Text, nullable=False)


class ErrorLog(TimestampedUUIDMixin, Base):
    __tablename__ = "error_logs"
    level: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(80))
    error_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class WebhookLog(TimestampedUUIDMixin, Base):
    __tablename__ = "webhook_logs"
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiKey(TimestampedUUIDMixin, Base):
    __tablename__ = "api_keys"
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyKey(TimestampedUUIDMixin, Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    request_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    response_payload: Mapped[JsonDict | None] = mapped_column(JSONB)
    status_code: Mapped[int | None] = mapped_column(Integer)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryPool(TimestampedUUIDMixin, Base):
    __tablename__ = "inventory_pools"
    product_variant_id: Mapped[UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(48), nullable=False)
    provider_key: Mapped[str | None] = mapped_column(String(120))
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unlimited_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)


class InventoryAsset(TimestampedUUIDMixin, Base):
    __tablename__ = "inventory_assets"
    __table_args__ = (UniqueConstraint("pool_id", "payload_fingerprint", name="uq_inventory_asset_fingerprint"),)
    pool_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_pools.id", ondelete="CASCADE"), index=True, nullable=False)
    payload_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", index=True, nullable=False)
    reserved_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    reserved_order_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("order_items.id", ondelete="SET NULL"), unique=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    asset_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class InventoryReservation(TimestampedUUIDMixin, Base):
    __tablename__ = "inventory_reservations"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    order_item_id: Mapped[UUID] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), unique=True, nullable=False)
    pool_id: Mapped[UUID | None] = mapped_column(ForeignKey("inventory_pools.id", ondelete="SET NULL"))
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("inventory_assets.id", ondelete="SET NULL"), unique=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="reserved", index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentAttempt(TimestampedUUIDMixin, Base):
    __tablename__ = "payment_attempts"
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True, nullable=False)
    verification_id: Mapped[UUID | None] = mapped_column(ForeignKey("payment_verifications.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    submitted_reference_hash: Mapped[str | None] = mapped_column(String(64))
    failure_code: Mapped[str | None] = mapped_column(String(120))
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    provider_response: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)


class FraudSignal(TimestampedUUIDMixin, Base):
    __tablename__ = "fraud_signals"
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invoice(TimestampedUUIDMixin, Base):
    __tablename__ = "invoices"
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invoice_data: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)


class Receipt(TimestampedUUIDMixin, Base):
    __tablename__ = "receipts"
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), unique=True, nullable=False)
    transaction_id: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"))
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_data: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)


class OutboxEvent(TimestampedUUIDMixin, Base):
    __tablename__ = "outbox_events"
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    topic: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    partition_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    audience: Mapped[str] = mapped_column(String(32), default="internal", nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(120), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(120))
    trace_id: Mapped[str | None] = mapped_column(String(120), index=True)
    cache_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    payload: Mapped[JsonDict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(160))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class EventDelivery(TimestampedUUIDMixin, Base):
    __tablename__ = "event_deliveries"
    __table_args__ = (UniqueConstraint("outbox_event_id", "destination", name="uq_event_delivery_destination"),)
    outbox_event_id: Mapped[UUID] = mapped_column(ForeignKey("outbox_events.id", ondelete="CASCADE"), index=True, nullable=False)
    destination: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    external_id: Mapped[str | None] = mapped_column(String(255))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class EventConsumerCheckpoint(TimestampedUUIDMixin, Base):
    __tablename__ = "event_consumer_checkpoints"
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    last_stream_id: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(32), default="healthy", nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumer_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONB, default=dict, nullable=False)


class CacheInvalidationLog(TimestampedUUIDMixin, Base):
    __tablename__ = "cache_invalidation_logs"
    outbox_event_id: Mapped[UUID] = mapped_column(ForeignKey("outbox_events.id", ondelete="CASCADE"), unique=True, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
