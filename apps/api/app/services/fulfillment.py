from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.observability import FULFILLMENTS
from app.models import (
    AnalyticsEvent,
    DeliveryLog,
    DeliveryQueue,
    InventoryPool,
    InventoryReservation,
    Order,
    OrderItem,
    ProductVariant,
)
from app.services.configuration import ConfigurationService
from app.services.delivery_providers import DeliveryContext, DeliveryProviderRegistry
from app.services.inventory import InventoryService
from app.services.outbox import OutboxService


class FulfillmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.configuration = ConfigurationService(session)
        self.inventory = InventoryService(session)
        self.outbox = OutboxService(session)
        self.providers = DeliveryProviderRegistry(session)

    async def enqueue_paid_order(self, order: Order) -> list[DeliveryQueue]:
        deliveries: list[DeliveryQueue] = []
        items = list((await self.session.scalars(select(OrderItem).where(OrderItem.order_id == order.id))).all())
        for item in items:
            existing = await self.session.scalar(
                select(DeliveryQueue).where(DeliveryQueue.order_item_id == item.id).with_for_update()
            )
            if existing:
                deliveries.append(existing)
                continue
            variant = await self.session.get(ProductVariant, item.product_variant_id)
            if variant is None:
                raise ValueError("delivery.variant_missing")
            reservation = await self.session.scalar(
                select(InventoryReservation).where(InventoryReservation.order_item_id == item.id)
            )
            pool = await self.session.get(InventoryPool, reservation.pool_id) if reservation and reservation.pool_id else None
            delivery = DeliveryQueue(
                order_id=order.id,
                order_item_id=item.id,
                delivery_type=variant.delivery_type,
                provider_key=pool.provider_key if pool else None,
                status="queued",
                next_attempt_at=datetime.now(UTC),
            )
            self.session.add(delivery)
            deliveries.append(delivery)
        order.status = "fulfilling"
        self.outbox.add(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.status_changed",
            payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
        )
        return deliveries

    async def process_next(self) -> bool:
        delivery = await self.session.scalar(
            select(DeliveryQueue)
            .where(
                DeliveryQueue.status.in_(["queued", "retrying"]),
                (DeliveryQueue.next_attempt_at.is_(None)) | (DeliveryQueue.next_attempt_at <= datetime.now(UTC)),
            )
            .order_by(DeliveryQueue.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if delivery is None:
            return False
        delivery.status = "processing"
        delivery.attempt_count += 1
        delivery.next_attempt_at = None
        delivery_id = delivery.id
        await self.session.commit()
        try:
            payload = await self._deliver(delivery_id)
            await self._complete(delivery_id, payload)
            FULFILLMENTS.labels("completed").inc()
        except Exception as exc:
            await self.session.rollback()
            await self._fail(delivery_id, exc)
            FULFILLMENTS.labels("failed").inc()
        return True

    async def _deliver(self, delivery_id) -> str:
        delivery = await self.session.get(DeliveryQueue, delivery_id)
        if delivery is None:
            raise ValueError("delivery.not_found")
        item = await self.session.get(OrderItem, delivery.order_item_id)
        if item is None:
            raise ValueError("delivery.order_item_missing")

        if delivery.delivery_type == "wallet_topup":
            from decimal import Decimal
            from app.models import Wallet, WalletTransaction
            order = await self.session.get(Order, delivery.order_id)
            if order is None:
                raise ValueError("delivery.order_missing")
            credit_amount = item.unit_price_amount * item.quantity
            wallet_result = await self.session.execute(
                select(Wallet).where(Wallet.user_id == order.user_id).with_for_update()
            )
            user_wallet = wallet_result.scalar_one_or_none()
            if user_wallet is None:
                user_wallet = Wallet(user_id=order.user_id, balance=Decimal("0.00"))
                self.session.add(user_wallet)
                await self.session.flush()
            user_wallet.balance += credit_amount
            wallet_tx = WalletTransaction(
                wallet_id=user_wallet.id,
                amount=credit_amount,
                type="top_up",
                description=f"Wallet top-up via order {order.order_number}",
                reference_id=order.id
            )
            self.session.add(wallet_tx)
            await self.session.flush()
            return f"Wallet topped up successfully with {credit_amount} USD. New balance: {user_wallet.balance} USD."

        # Check if we have direct/static delivery content in product metadata
        variant = await self.session.get(ProductVariant, item.product_variant_id)
        if variant and variant.product:
            # Priority 1: Queue of encrypted accounts
            encrypted_list = variant.product.product_metadata.get("delivery_content_list_encrypted")
            if isinstance(encrypted_list, list) and encrypted_list:
                first_encrypted = encrypted_list.pop(0)
                # Assign a copy back to trigger SQLAlchemy change tracking
                variant.product.product_metadata = {
                    **variant.product.product_metadata,
                    "delivery_content_list_encrypted": encrypted_list
                }
                
                from app.models import Inventory
                db_inventory = await self.session.scalar(
                    select(Inventory).where(Inventory.product_variant_id == variant.id).with_for_update()
                )
                if db_inventory:
                    db_inventory.quantity_available = len(encrypted_list)
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(db_inventory)
                
                await self.session.flush()
                return cipher.decrypt(first_encrypted)

            # Priority 2: Static text
            if variant.product.product_metadata.get("delivery_content_encrypted"):
                return cipher.decrypt(variant.product.product_metadata["delivery_content_encrypted"])

        reservation = await self.session.scalar(
            select(InventoryReservation).where(InventoryReservation.order_item_id == item.id)
        )
        provider = self.providers.resolve(delivery_type=delivery.delivery_type, provider_key=delivery.provider_key)
        return await provider.deliver(
            DeliveryContext(item=item, reservation=reservation, provider_key=delivery.provider_key)
        )

    async def _complete(self, delivery_id, payload: str) -> None:
        delivery = await self.session.get(DeliveryQueue, delivery_id, with_for_update=True)
        if delivery is None or delivery.status == "completed":
            return
        reservation = await self.session.scalar(
            select(InventoryReservation)
            .where(InventoryReservation.order_item_id == delivery.order_item_id)
            .with_for_update()
        )
        delivery.payload_encrypted = cipher.encrypt(payload)
        delivery.status = "completed"
        delivery.completed_at = datetime.now(UTC)
        delivery.last_error = None
        if reservation:
            await self.inventory.mark_delivered(reservation)
        self._log(delivery, "completed", "delivery.completed", {"attempt": delivery.attempt_count})
        await self._complete_order_if_ready(delivery.order_id)
        self.outbox.add(
            aggregate_type="delivery",
            aggregate_id=delivery.id,
            event_type="delivery.completed",
            payload={"delivery_id": str(delivery.id), "order_id": str(delivery.order_id)},
        )
        self.session.add(
            AnalyticsEvent(
                event_type="delivery.completed",
                source="automation",
                event_metadata={"delivery_id": str(delivery.id), "attempts": delivery.attempt_count},
            )
        )
        await self.session.commit()

    async def _fail(self, delivery_id, exc: Exception) -> None:
        delivery = await self.session.get(DeliveryQueue, delivery_id, with_for_update=True)
        if delivery is None or delivery.status == "completed":
            return
        automation = await self.configuration.automation()
        delivery.last_error = str(exc)[:2000]
        if delivery.attempt_count >= automation.delivery_max_attempts:
            delivery.status = "manual_review"
            delivery.next_attempt_at = None
            self._log(delivery, "manual_review", "delivery.manual_review", {"error": str(exc)[:500]})
            self.outbox.add(
                aggregate_type="delivery",
                aggregate_id=delivery.id,
                event_type="delivery.failed",
                payload={"delivery_id": str(delivery.id), "order_id": str(delivery.order_id), "error": str(exc)[:500]},
            )
        else:
            delivery.status = "retrying"
            delay = min(1800, (2 ** min(delivery.attempt_count, 10)) * 15) + random.randint(0, 15)
            delivery.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
            self._log(delivery, "retrying", "delivery.retrying", {"error": str(exc)[:500], "retry_seconds": delay})
        await self.session.commit()

    async def _complete_order_if_ready(self, order_id) -> None:
        remaining = await self.session.scalar(
            select(func.count(DeliveryQueue.id)).where(
                DeliveryQueue.order_id == order_id,
                DeliveryQueue.status != "completed",
            )
        )
        if (remaining or 0) == 0:
            order = await self.session.get(Order, order_id, with_for_update=True)
            if order:
                order.status = "completed"
                self.outbox.add(
                    aggregate_type="order",
                    aggregate_id=order.id,
                    event_type="order.completed",
                    payload={"order_id": str(order.id), "user_id": str(order.user_id)},
                )
                self.outbox.add(
                    aggregate_type="order",
                    aggregate_id=order.id,
                    event_type="order.status_changed",
                    payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
                )

    def _log(self, delivery: DeliveryQueue, status: str, message_key: str, metadata: dict) -> None:
        self.session.add(
            DeliveryLog(delivery_id=delivery.id, status=status, message_key=message_key, log_metadata=metadata)
        )
