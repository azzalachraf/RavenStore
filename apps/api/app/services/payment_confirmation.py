from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.payment_verifiers import VerificationResult
from app.models import AnalyticsEvent, Order, Payment, PaymentVerification, Transaction
from app.services.fulfillment import FulfillmentService
from app.services.inventory import InventoryService
from app.services.ledger import LedgerService
from app.services.outbox import OutboxService


class PaymentConfirmationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory = InventoryService(session)
        self.ledger = LedgerService(session)
        self.outbox = OutboxService(session)

    async def confirm(
        self,
        *,
        payment: Payment,
        verification: PaymentVerification,
        result: VerificationResult,
        reference_hash: str,
        source: str = "automation",
        actor_user_id: UUID | None = None,
    ) -> Transaction:
        transaction = Transaction(
            payment_id=payment.id,
            tx_hash=result.provider_reference or reference_hash,
            reference_hash=reference_hash,
            amount=result.amount,
            currency=payment.currency,
            network=payment.network,
            confirmations=result.confirmations,
            status="confirmed" if source == "automation" else "manually_confirmed",
            raw_payload={**result.raw_payload, "confirmation_source": source, "actor_user_id": str(actor_user_id) if actor_user_id else None},
        )
        self.session.add(transaction)
        await self.session.flush()
        payment.status = "confirmed"
        payment.confirmed_at = datetime.now(UTC)
        payment.failed_at = None
        payment.manual_review_reason = None
        verification.verification_status = "confirmed"
        verification.completed_at = datetime.now(UTC)
        verification.locked_at = None
        verification.failure_code = None
        verification.last_error = None
        order = await self.session.get(Order, payment.order_id, with_for_update=True)
        if order is None:
            raise ValueError("orders.not_found")
        order.status = "paid"
        await self.inventory.commit_for_order(order.id)
        await self.ledger.ensure_receipt(payment, transaction)
        self.outbox.add(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.status_changed",
            payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
        )
        await FulfillmentService(self.session).enqueue_paid_order(order)
        self.session.add(
            AnalyticsEvent(
                user_id=order.user_id,
                event_type="payment.confirmed",
                source=source,
                event_metadata={
                    "payment_id": str(payment.id),
                    "order_id": str(order.id),
                    "amount": str(payment.amount),
                    "network": payment.network,
                },
            )
        )
        self.outbox.add(
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type="payment.confirmed",
            payload={"payment_id": str(payment.id), "order_id": str(order.id), "user_id": str(order.user_id)},
        )
        return transaction
