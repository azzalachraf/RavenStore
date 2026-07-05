from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invoice, Order, Payment, Receipt, Transaction


class LedgerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_invoice(self, order: Order) -> Invoice:
        result = await self.session.execute(select(Invoice).where(Invoice.order_id == order.id))
        invoice = result.scalar_one_or_none()
        if invoice:
            return invoice
        invoice = Invoice(
            order_id=order.id,
            invoice_number=f"INV-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(10).upper()}",
            subtotal_amount=order.subtotal_amount,
            discount_amount=order.discount_amount,
            total_amount=order.total_amount,
            currency=order.currency,
            issued_at=datetime.now(UTC),
            invoice_data={"order_number": order.order_number, "status": order.status},
        )
        self.session.add(invoice)
        return invoice

    async def ensure_receipt(self, payment: Payment, transaction: Transaction) -> Receipt:
        result = await self.session.execute(select(Receipt).where(Receipt.payment_id == payment.id))
        receipt = result.scalar_one_or_none()
        if receipt:
            return receipt
        receipt = Receipt(
            payment_id=payment.id,
            transaction_id=transaction.id,
            receipt_number=f"RCT-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(10).upper()}",
            amount=transaction.amount,
            currency=transaction.currency,
            issued_at=datetime.now(UTC),
            receipt_data={"network": transaction.network, "transaction_hash": transaction.tx_hash},
        )
        self.session.add(receipt)
        return receipt
