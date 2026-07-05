from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AnalyticsEvent, DeliveryQueue, Order, OutboxEvent, Payment, PaymentVerification, RefreshToken
from app.services.inventory import InventoryService
from app.services.outbox import OutboxService


class CleanupWorker:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.inventory = InventoryService(session)
        self.outbox = OutboxService(session)

    async def run(self) -> None:
        now = datetime.now(UTC)
        await self.session.execute(delete(RefreshToken).where(RefreshToken.expires_at < now))
        await self.inventory.release_expired()
        await self._expire_abandoned_payments(now)
        await self._recover_stale_jobs(now)
        await self.session.execute(
            delete(OutboxEvent).where(
                OutboxEvent.status == "processed",
                OutboxEvent.processed_at < now - timedelta(days=settings.event_outbox_retention_days),
            )
        )
        await self.session.commit()

    async def _expire_abandoned_payments(self, now: datetime) -> None:
        payments = list(
            (
                await self.session.scalars(
                    select(Payment)
                    .where(Payment.status == "pending", Payment.expires_at < now)
                    .limit(500)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for payment in payments:
            payment.status = "expired"
            payment.failed_at = now
            order = await self.session.get(Order, payment.order_id, with_for_update=True)
            if order and order.status == "pending_payment":
                order.status = "payment_failed"
                self.session.add(
                    AnalyticsEvent(
                        user_id=order.user_id,
                        event_type="checkout.abandoned",
                        source="automation",
                        event_metadata={"order_id": str(order.id), "payment_id": str(payment.id)},
                    )
                )
                self.outbox.add(
                    aggregate_type="order",
                    aggregate_id=order.id,
                    event_type="order.status_changed",
                    payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
                )
            await self.inventory.release_for_order(payment.order_id, reason="checkout_expired")
            self.outbox.add(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type="payment.failed",
                payload={"payment_id": str(payment.id), "order_id": str(payment.order_id), "reason": "expired"},
            )

    async def _recover_stale_jobs(self, now: datetime) -> None:
        stale_at = now - timedelta(minutes=10)
        verifications = list(
            (
                await self.session.scalars(
                    select(PaymentVerification)
                    .where(
                        PaymentVerification.verification_status == "processing",
                        PaymentVerification.locked_at < stale_at,
                    )
                    .limit(500)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for verification in verifications:
            verification.verification_status = "retrying"
            verification.locked_at = None
            verification.next_attempt_at = now
            verification.last_error = "payments.worker_lease_expired"
        deliveries = list(
            (
                await self.session.scalars(
                    select(DeliveryQueue)
                    .where(DeliveryQueue.status == "processing", DeliveryQueue.updated_at < stale_at)
                    .limit(500)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for delivery in deliveries:
            delivery.status = "retrying"
            delivery.next_attempt_at = now
            delivery.last_error = "delivery.worker_lease_expired"
        outbox_events = list(
            (
                await self.session.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.status == "processing", OutboxEvent.claimed_at < stale_at)
                    .limit(500)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for event in outbox_events:
            event.status = "retrying"
            event.available_at = now
            event.claimed_at = None
            event.claimed_by = None
            event.last_error = "events.worker_lease_expired"
