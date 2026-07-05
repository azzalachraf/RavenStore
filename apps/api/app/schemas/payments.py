from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import APIModel, JsonDict, TimestampedOut


class PaymentRequestIn(APIModel):
    order_id: UUID
    method: str = Field(min_length=2, max_length=64, pattern="^[a-z0-9_]+$")


class PaymentOut(TimestampedOut):
    order_id: UUID
    provider: str
    network: str
    status: str
    amount: Decimal
    currency: str
    payment_address: str | None
    payment_url: str | None
    confirmed_at: datetime | None
    expires_at: datetime


class PaymentCreatedOut(APIModel):
    payment: PaymentOut
    payment_token: str
    payment_reference: str
    message_key: str = "payments.created"


class PaymentVerificationIn(APIModel):
    payment_token: str = Field(min_length=16, max_length=512)
    submitted_reference: str | None = Field(default=None, min_length=6, max_length=255)
    tx_hash: str | None = Field(default=None, min_length=6, max_length=255)
    binance_order_id: str | None = Field(default=None, min_length=6, max_length=255)

    @model_validator(mode="after")
    def normalize_reference(self):
        self.submitted_reference = self.submitted_reference or self.tx_hash or self.binance_order_id
        return self


class PaymentAttemptOut(TimestampedOut):
    payment_id: UUID
    source: str
    status: str
    failure_code: str | None
    risk_score: int
    duration_ms: int | None


class InvoiceOut(TimestampedOut):
    order_id: UUID
    invoice_number: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    issued_at: datetime
    invoice_data: JsonDict


class ReceiptOut(TimestampedOut):
    payment_id: UUID
    transaction_id: UUID | None
    receipt_number: str
    amount: Decimal
    currency: str
    issued_at: datetime
    receipt_data: JsonDict


class TransactionOut(TimestampedOut):
    payment_id: UUID
    tx_hash: str
    amount: Decimal
    currency: str
    network: str
    confirmations: int
    status: str
