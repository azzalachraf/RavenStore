from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Audience = Literal["public", "customer", "admin", "internal"]


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: str
    topic: str
    schema_version: int = 1
    aggregate_type: str
    aggregate_id: UUID
    partition_key: str
    audience: Audience
    occurred_at: datetime
    correlation_id: str | None = None
    causation_id: str | None = None
    trace_id: str | None = None
    cache_tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class EventPolicy(BaseModel):
    topic: str
    audience: Audience
    cache_tags: list[str]


EVENT_POLICIES: dict[str, EventPolicy] = {
    "product": EventPolicy(topic="catalog", audience="public", cache_tags=["products"]),
    "variant": EventPolicy(topic="catalog", audience="public", cache_tags=["products"]),
    "category": EventPolicy(topic="catalog", audience="public", cache_tags=["categories", "products"]),
    "inventory": EventPolicy(topic="inventory", audience="public", cache_tags=["inventory", "products"]),
    "translation": EventPolicy(topic="localization", audience="public", cache_tags=["translations"]),
    "language": EventPolicy(topic="localization", audience="public", cache_tags=["languages", "translations"]),
    "settings": EventPolicy(topic="settings", audience="public", cache_tags=["settings"]),
    "order": EventPolicy(topic="orders", audience="customer", cache_tags=["orders"]),
    "payment": EventPolicy(topic="payments", audience="customer", cache_tags=["orders", "payments", "analytics"]),
    "delivery": EventPolicy(topic="fulfillment", audience="customer", cache_tags=["orders", "deliveries"]),
    "support": EventPolicy(topic="support", audience="customer", cache_tags=["support"]),
    "referral": EventPolicy(topic="referrals", audience="customer", cache_tags=["referrals"]),
    "notification": EventPolicy(topic="notifications", audience="customer", cache_tags=["notifications"]),
    "system": EventPolicy(topic="system", audience="admin", cache_tags=["health"]),
}


def policy_for(event_type: str) -> EventPolicy:
    prefix = event_type.split(".", 1)[0]
    return EVENT_POLICIES.get(prefix, EventPolicy(topic="system", audience="internal", cache_tags=[]))
