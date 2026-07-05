from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import policy_for
from app.models import OutboxEvent


class OutboxService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(
        self,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict,
        audience: str | None = None,
        cache_tags: list[str] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> OutboxEvent:
        policy = policy_for(event_type)
        context = structlog.contextvars.get_contextvars()
        event = OutboxEvent(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            topic=policy.topic,
            schema_version=1,
            partition_key=f"{aggregate_type}:{aggregate_id}",
            audience=audience or policy.audience,
            correlation_id=correlation_id or context.get("request_id"),
            causation_id=causation_id,
            trace_id=context.get("trace_id") or context.get("request_id"),
            cache_tags=list(dict.fromkeys([*policy.cache_tags, *(cache_tags or [])])),
            payload=payload,
            status="pending",
            available_at=datetime.now(UTC),
        )
        self.session.add(event)
        return event
