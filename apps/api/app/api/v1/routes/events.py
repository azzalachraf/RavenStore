from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from app.core.database import AsyncSessionLocal
from app.core.events import EventEnvelope
from app.core.dependencies import db_session, require_roles, require_telegram_service_or_roles
from app.core.security import decode_access_token, hash_secret
from app.infrastructure.redis_runtime import redis_runtime
from app.models import ApiKey, EventConsumerCheckpoint, EventDelivery, OutboxEvent, Role, User
from app.services.audit import AuditService

router = APIRouter()


@dataclass(frozen=True)
class EventPrincipal:
    user_id: UUID | None = None
    role: str | None = None


class ConsumerCheckpointIn(BaseModel):
    last_stream_id: str | None = Field(default=None, max_length=80)
    status: str = Field(default="healthy", max_length=32)
    metadata: dict = Field(default_factory=dict)


@router.get("/stream")
async def event_stream(
    request: Request,
    topics: str | None = Query(default=None, max_length=500),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
):
    principal = await _principal(request)
    allowed_topics = {value.strip() for value in topics.split(",") if value.strip()} if topics else None

    async def generate():
        yield "retry: 3000\n\n"
        source = (
            redis_runtime.stream(last_event_id or "$")
            if redis_runtime.available
            else _database_stream(last_event_id)
        )
        async for stream_id, event in source:
            if await request.is_disconnected():
                break
            if event is None:
                yield ": heartbeat\n\n"
                continue
            if allowed_topics and event.get("topic") not in allowed_topics:
                continue
            if not _can_receive(principal, event):
                continue
            body = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
            yield f"id: {stream_id}\nevent: {event['event_type']}\ndata: {body}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _database_stream(last_event_id: str | None):
    cursor_time = datetime.now(UTC)
    cursor_id: UUID | None = None
    if last_event_id:
        try:
            cursor_id = UUID(last_event_id)
        except ValueError:
            cursor_id = None
        if cursor_id:
            async with AsyncSessionLocal() as session:
                previous = await session.get(OutboxEvent, cursor_id)
                if previous:
                    cursor_time = previous.created_at
    while True:
        async with AsyncSessionLocal() as session:
            statement = select(OutboxEvent).where(OutboxEvent.created_at > cursor_time)
            if cursor_id:
                statement = select(OutboxEvent).where(
                    or_(
                        OutboxEvent.created_at > cursor_time,
                        (OutboxEvent.created_at == cursor_time) & (OutboxEvent.id > cursor_id),
                    )
                )
            rows = list((await session.scalars(statement.order_by(OutboxEvent.created_at, OutboxEvent.id).limit(100))).all())
        if not rows:
            await asyncio.sleep(1)
            yield None, None
            continue
        for event in rows:
            cursor_time = event.created_at
            cursor_id = event.id
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
            yield str(event.id), envelope.model_dump(mode="json")


@router.put("/consumers/{consumer_name}/checkpoint")
async def update_consumer_checkpoint(
    consumer_name: str,
    payload: ConsumerCheckpointIn,
    session: AsyncSession = Depends(db_session),
    _=Depends(require_telegram_service_or_roles("Owner", "Admin")),
):
    checkpoint = await session.scalar(
        select(EventConsumerCheckpoint).where(EventConsumerCheckpoint.name == consumer_name).with_for_update()
    )
    if checkpoint is None:
        checkpoint = EventConsumerCheckpoint(
            name=consumer_name,
            heartbeat_at=datetime.now(UTC),
            consumer_metadata={},
        )
        session.add(checkpoint)
    checkpoint.last_stream_id = payload.last_stream_id
    checkpoint.status = payload.status
    checkpoint.heartbeat_at = datetime.now(UTC)
    checkpoint.consumer_metadata = payload.metadata
    await session.commit()
    return {"message_key": "events.checkpoint_updated"}


@router.get("/health")
async def event_health(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator")),
):
    now = datetime.now(UTC)
    pending = await session.scalar(
        select(func.count(OutboxEvent.id)).where(OutboxEvent.status.in_(["pending", "retrying", "processing"]))
    )
    dead_letters = await session.scalar(
        select(func.count(OutboxEvent.id)).where(OutboxEvent.status == "dead_letter")
    )
    failed_deliveries = await session.scalar(
        select(func.count(EventDelivery.id)).where(EventDelivery.status == "failed")
    )
    stale_consumers = await session.scalar(
        select(func.count(EventConsumerCheckpoint.id)).where(
            EventConsumerCheckpoint.heartbeat_at < now - timedelta(minutes=5)
        )
    )
    return {
        "redis": "healthy" if await redis_runtime.ping() else "unavailable",
        "outbox_pending": pending or 0,
        "dead_letters": dead_letters or 0,
        "failed_deliveries": failed_deliveries or 0,
        "stale_consumers": stale_consumers or 0,
        "transport_metrics": await redis_runtime.metrics(),
    }


@router.get("/dead-letters")
async def dead_letters(
    limit: int = 100,
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin")),
):
    events = await session.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.status == "dead_letter")
        .order_by(OutboxEvent.dead_lettered_at.desc())
        .limit(min(max(limit, 1), 500))
    )
    return [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id),
            "attempt_count": event.attempt_count,
            "last_error": event.last_error,
            "dead_lettered_at": event.dead_lettered_at,
            "trace_id": event.trace_id,
        }
        for event in events.all()
    ]


@router.post("/{event_id}/replay", status_code=202)
async def replay_event(
    event_id: UUID,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    event = await session.get(OutboxEvent, event_id, with_for_update=True)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="events.not_found")
    event.status = "pending"
    event.attempt_count = 0
    event.available_at = datetime.now(UTC)
    event.claimed_at = None
    event.claimed_by = None
    event.dead_lettered_at = None
    event.last_error = None
    AuditService(session).log(
        actor_user_id=admin.id,
        action="event.replay",
        resource_type="outbox_event",
        resource_id=event.id,
        metadata={"event_type": event.event_type},
    )
    await session.commit()
    return {"message_key": "events.replay_queued"}


async def _principal(request: Request) -> EventPrincipal:
    authorization = request.headers.get("Authorization", "")
    api_key_value = request.headers.get("X-API-Key")
    user_id: UUID | None = None
    if authorization.lower().startswith("bearer "):
        try:
            user_id = UUID(decode_access_token(authorization[7:])["sub"])
        except (KeyError, ValueError):
            return EventPrincipal()
    async with AsyncSessionLocal() as session:
        if user_id is None and api_key_value:
            api_key = await session.scalar(
                select(ApiKey).where(ApiKey.key_hash == hash_secret(api_key_value), ApiKey.revoked_at.is_(None))
            )
            user_id = api_key.owner_user_id if api_key else None
        if user_id is None:
            return EventPrincipal()
        user = await session.get(User, user_id)
        if user is None or user.status != "active":
            return EventPrincipal()
        role = await session.get(Role, user.role_id)
        return EventPrincipal(user_id=user.id, role=role.name if role else None)


def _can_receive(principal: EventPrincipal, event: dict) -> bool:
    audience = event.get("audience")
    if audience == "public":
        return True
    if principal.role in {"Owner", "Admin", "Moderator", "Support"}:
        return audience in {"public", "customer", "admin"}
    if audience == "customer" and principal.user_id:
        return str(event.get("payload", {}).get("user_id")) == str(principal.user_id)
    return False
