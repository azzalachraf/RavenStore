from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from fastapi import status
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models import IdempotencyKey


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        key = request.headers.get("Idempotency-Key")
        if request.method not in {"POST", "PATCH", "PUT"} or not key:
            return await call_next(request)

        body = await request.body()
        authorization = request.headers.get("Authorization", "")
        authorization_scope = authorization or request.headers.get("X-API-Key") or "anonymous"
        if authorization.lower().startswith("bearer "):
            try:
                authorization_scope = f"user:{decode_access_token(authorization[7:])['sub']}"
            except (KeyError, ValueError):
                pass
        stored_key = hashlib.sha256(f"{authorization_scope}:{key}".encode()).hexdigest()
        request_hash = hashlib.sha256(
            body + request.method.encode() + request.url.path.encode() + request.url.query.encode()
        ).hexdigest()

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(IdempotencyKey).where(IdempotencyKey.key == stored_key))
            record = result.scalar_one_or_none()
            if record and record.request_hash != request_hash:
                return ORJSONResponse(
                    {"error": {"message_key": "idempotency.key_reused_with_different_request"}},
                    status_code=status.HTTP_409_CONFLICT,
                )
            if record and record.response_payload is not None and record.status_code is not None:
                return ORJSONResponse(record.response_payload, status_code=record.status_code)
            if record and record.locked_until and record.locked_until > datetime.now(UTC):
                return ORJSONResponse(
                    {"error": {"message_key": "idempotency.request_in_progress"}},
                    status_code=status.HTTP_409_CONFLICT,
                )
            if record is None:
                record = IdempotencyKey(
                    key=stored_key,
                    user_id=None,
                    request_hash=request_hash,
                    locked_until=datetime.now(UTC) + timedelta(minutes=2),
                )
                session.add(record)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    concurrent = await session.scalar(select(IdempotencyKey).where(IdempotencyKey.key == stored_key))
                    if concurrent and concurrent.request_hash != request_hash:
                        return ORJSONResponse(
                            {"error": {"message_key": "idempotency.key_reused_with_different_request"}},
                            status_code=status.HTTP_409_CONFLICT,
                        )
                    return ORJSONResponse(
                        {"error": {"message_key": "idempotency.request_in_progress"}},
                        status_code=status.HTTP_409_CONFLICT,
                    )

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        replay_request = Request(request.scope, receive)
        response = await call_next(replay_request)
        chunks = [chunk async for chunk in response.body_iterator]
        response_body = b"".join(chunks)
        payload = self._json_payload(response_body)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(IdempotencyKey).where(IdempotencyKey.key == stored_key))
            stored = result.scalar_one_or_none()
            if stored and payload is not None and response.status_code < 500:
                stored.response_payload = payload
                stored.status_code = response.status_code
                stored.locked_until = None
                await session.commit()

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    def _json_payload(self, body: bytes) -> dict | list | None:
        try:
            value = json.loads(body.decode())
            return value if isinstance(value, dict | list) else None
        except Exception:
            return None
