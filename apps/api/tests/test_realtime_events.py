from __future__ import annotations

import asyncio
from uuid import uuid4

import structlog

from app.api.v1.routes.events import EventPrincipal, _can_receive
from app.core.events import EventEnvelope, policy_for
from app.infrastructure.redis_runtime import RedisRuntime
from app.services.outbox import OutboxService


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def test_event_policy_maps_catalog_to_public_cache_invalidation() -> None:
    policy = policy_for("product.price_changed")

    assert policy.topic == "catalog"
    assert policy.audience == "public"
    assert policy.cache_tags == ["products"]


def test_outbox_service_builds_versioned_traceable_event() -> None:
    session = FakeSession()
    structlog.contextvars.bind_contextvars(request_id="request-123")
    aggregate_id = uuid4()
    try:
        event = OutboxService(session).add(
            aggregate_type="product",
            aggregate_id=aggregate_id,
            event_type="product.updated",
            payload={"product_id": str(aggregate_id)},
            cache_tags=["product:detail"],
        )
    finally:
        structlog.contextvars.clear_contextvars()

    assert session.added == [event]
    assert event.topic == "catalog"
    assert event.audience == "public"
    assert event.schema_version == 1
    assert event.trace_id == "request-123"
    assert event.cache_tags == ["products", "product:detail"]


def test_event_audience_prevents_cross_customer_delivery() -> None:
    customer_id = uuid4()
    other_id = uuid4()
    event = {"audience": "customer", "payload": {"user_id": str(customer_id)}}

    assert _can_receive(EventPrincipal(user_id=customer_id, role="Customer"), event)
    assert not _can_receive(EventPrincipal(user_id=other_id, role="Customer"), event)
    assert _can_receive(EventPrincipal(user_id=other_id, role="Admin"), event)
    assert not _can_receive(EventPrincipal(), event)


async def test_local_event_stream_fallback_delivers_envelope() -> None:
    runtime = RedisRuntime()
    stream = runtime.stream("$")
    waiting = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    event_id = uuid4()
    envelope = EventEnvelope(
        event_id=event_id,
        event_type="product.updated",
        topic="catalog",
        aggregate_type="product",
        aggregate_id=uuid4(),
        partition_key="product:test",
        audience="public",
        occurred_at="2026-07-04T00:00:00Z",
        cache_tags=["products"],
        payload={},
    )
    stream_id = await runtime.publish_event(envelope.model_dump(mode="json"))
    received_id, received = await asyncio.wait_for(waiting, timeout=1)
    await stream.aclose()

    assert received_id == stream_id
    assert received and received["event_id"] == str(event_id)
