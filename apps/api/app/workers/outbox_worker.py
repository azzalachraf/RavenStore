from __future__ import annotations

import os
import socket
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.events import EventEnvelope
from app.core.observability import OUTBOX_EVENTS
from app.infrastructure.redis_runtime import redis_runtime
from app.models import (
    CacheInvalidationLog,
    ErrorLog,
    EventDelivery,
    Notification,
    Order,
    OutboxEvent,
    Role,
    User,
)

CUSTOMER_MESSAGES = {
    "order.created": ("notifications.order_created.title", "notifications.order_created.body"),
    "payment.confirmed": ("notifications.payment_confirmed.title", "notifications.payment_confirmed.body"),
    "payment.failed": ("notifications.payment_failed.title", "notifications.payment_failed.body"),
    "delivery.completed": ("notifications.delivery_completed.title", "notifications.delivery_completed.body"),
    "order.completed": ("notifications.order_completed.title", "notifications.order_completed.body"),
    "support.reply_added": ("notifications.support_reply.title", "notifications.support_reply.body"),
    "referral.rewarded": ("notifications.referral_reward.title", "notifications.referral_reward.body"),
}

ADMIN_MESSAGES = {
    "order.created": ("notifications.new_order.title", "notifications.new_order.body"),
    "payment.manual_review": ("notifications.payment_review.title", "notifications.payment_review.body"),
    "payment.failed": ("notifications.admin_payment_failed.title", "notifications.admin_payment_failed.body"),
    "delivery.failed": ("notifications.delivery_failed.title", "notifications.delivery_failed.body"),
    "inventory.low_stock": ("notifications.low_stock.title", "notifications.low_stock.body"),
    "support.ticket_created": ("notifications.support_request.title", "notifications.support_request.body"),
    "system.alert": ("notifications.system_alert.title", "notifications.system_alert.body"),
}


class OutboxWorker:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"

    async def process_next(self) -> bool:
        event = await self.session.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.status.in_(["pending", "retrying"]),
                OutboxEvent.available_at <= datetime.now(UTC),
            )
            .order_by(OutboxEvent.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if event is None:
            return False
        event.status = "processing"
        event.attempt_count += 1
        event.claimed_at = datetime.now(UTC)
        event.claimed_by = self.worker_id
        event_id = event.id
        await self.session.commit()

        started = perf_counter()
        try:
            stream_id = await self._dispatch(event_id)
            await self._complete(event_id, stream_id, int((perf_counter() - started) * 1000))
            OUTBOX_EVENTS.labels("published").inc()
        except Exception as exc:
            await self.session.rollback()
            await self._fail(event_id, exc, int((perf_counter() - started) * 1000))
            OUTBOX_EVENTS.labels("failed").inc()
        return True

    async def _dispatch(self, event_id: UUID) -> str:
        event = await self.session.get(OutboxEvent, event_id)
        if event is None:
            raise ValueError("events.not_found")
        user_id = await self._customer_id(event)
        if user_id and not event.payload.get("user_id"):
            event.payload = {**event.payload, "user_id": str(user_id)}
        invalidation = await self.session.scalar(
            select(CacheInvalidationLog).where(CacheInvalidationLog.outbox_event_id == event.id)
        )
        if invalidation is None:
            invalidation = CacheInvalidationLog(
                outbox_event_id=event.id,
                tags=event.cache_tags,
                status="processing",
            )
            self.session.add(invalidation)
        await redis_runtime.invalidate(event.cache_tags)
        invalidation.status = "completed"
        invalidation.invalidated_at = datetime.now(UTC)
        invalidation.last_error = None
        envelope = EventEnvelope(
            event_id=event.id,
            event_type=event.event_type,
            topic=event.topic,
            schema_version=event.schema_version,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            partition_key=event.partition_key,
            audience=event.audience,
            occurred_at=event.created_at,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            trace_id=event.trace_id,
            cache_tags=event.cache_tags,
            payload=event.payload,
        )
        return await redis_runtime.publish_event(envelope.model_dump(mode="json"))

    async def _complete(self, event_id: UUID, stream_id: str, latency_ms: int) -> None:
        event = await self.session.get(OutboxEvent, event_id, with_for_update=True)
        if event is None or event.status == "processed":
            return
        await self._create_notifications(event)
        delivery = await self.session.scalar(
            select(EventDelivery).where(
                EventDelivery.outbox_event_id == event.id,
                EventDelivery.destination == "redis_stream",
            )
        )
        if delivery is None:
            delivery = EventDelivery(
                outbox_event_id=event.id,
                destination="redis_stream",
                status="delivered",
                attempt_count=event.attempt_count,
            )
            self.session.add(delivery)
        delivery.status = "delivered"
        delivery.attempt_count = event.attempt_count
        delivery.latency_ms = latency_ms
        delivery.external_id = stream_id
        delivery.delivered_at = datetime.now(UTC)
        delivery.last_error = None
        event.status = "processed"
        event.published_at = datetime.now(UTC)
        event.processed_at = datetime.now(UTC)
        event.claimed_at = None
        event.claimed_by = None
        event.last_error = None
        await self.session.commit()

    async def _fail(self, event_id: UUID, exc: Exception, latency_ms: int) -> None:
        event = await self.session.get(OutboxEvent, event_id, with_for_update=True)
        if event is None:
            return
        event.last_error = str(exc)[:2000]
        event.claimed_at = None
        event.claimed_by = None
        delivery = await self.session.scalar(
            select(EventDelivery).where(
                EventDelivery.outbox_event_id == event.id,
                EventDelivery.destination == "redis_stream",
            )
        )
        if delivery is None:
            delivery = EventDelivery(
                outbox_event_id=event.id,
                destination="redis_stream",
                status="failed",
            )
            self.session.add(delivery)
        delivery.status = "failed"
        delivery.attempt_count = event.attempt_count
        delivery.latency_ms = latency_ms
        delivery.last_error = str(exc)[:2000]
        if event.attempt_count >= settings.event_worker_max_attempts:
            event.status = "dead_letter"
            event.dead_lettered_at = datetime.now(UTC)
            self.session.add(
                ErrorLog(
                    level="error",
                    message="events.delivery_dead_lettered",
                    trace_id=event.trace_id,
                    error_metadata={"event_id": str(event.id), "event_type": event.event_type, "error": str(exc)[:1000]},
                )
            )
            await self._notify_admins(
                event,
                title_key="notifications.system_alert.title",
                body_key="notifications.system_alert.body",
            )
        else:
            event.status = "retrying"
            event.available_at = datetime.now(UTC) + timedelta(seconds=min(1800, 2**event.attempt_count * 5))
        await self.session.commit()

    async def _create_notifications(self, event: OutboxEvent) -> None:
        user_id = await self._customer_id(event)
        message = CUSTOMER_MESSAGES.get(event.event_type)
        if user_id and message:
            await self._add_notifications(user_id=user_id, event=event, title_key=message[0], body_key=message[1])
        admin_message = ADMIN_MESSAGES.get(event.event_type)
        if admin_message:
            await self._notify_admins(event, title_key=admin_message[0], body_key=admin_message[1])

    async def _notify_admins(self, event: OutboxEvent, *, title_key: str, body_key: str) -> None:
        admins = await self.session.scalars(
            select(User.id).join(Role, Role.id == User.role_id).where(
                Role.name.in_(["Owner", "Admin"]),
                User.status == "active",
            )
        )
        for admin_id in admins.all():
            await self._add_notifications(
                user_id=admin_id,
                event=event,
                title_key=title_key,
                body_key=body_key,
            )

    async def _customer_id(self, event: OutboxEvent) -> UUID | None:
        raw_user_id = event.payload.get("user_id")
        if raw_user_id:
            return UUID(str(raw_user_id))
        raw_order_id = event.payload.get("order_id")
        if raw_order_id:
            return await self.session.scalar(select(Order.user_id).where(Order.id == UUID(str(raw_order_id))))
        return None

    async def _add_notifications(
        self,
        *,
        user_id: UUID,
        event: OutboxEvent,
        title_key: str,
        body_key: str,
    ) -> None:
        payload = {**event.payload, "event_id": str(event.id), "event_type": event.event_type}
        for channel, status in (("website", "ready"), ("telegram", "queued")):
            existing = await self.session.scalar(
                select(Notification.id).where(
                    Notification.source_event_id == event.id,
                    Notification.user_id == user_id,
                    Notification.channel == channel,
                )
            )
            if existing:
                continue
            self.session.add(
                Notification(
                    source_event_id=event.id,
                    user_id=user_id,
                    channel=channel,
                    title_key=title_key,
                    body_key=body_key,
                    status=status,
                    payload=payload,
                    next_attempt_at=datetime.now(UTC) if channel == "telegram" else None,
                )
            )
