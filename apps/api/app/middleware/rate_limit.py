from __future__ import annotations

import time
from collections import defaultdict

from fastapi import status
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.network import client_ip
from app.infrastructure.redis_runtime import redis_runtime


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._memory: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health") or request.method == "OPTIONS":
            return await call_next(request)
        identity = self._identity(request)
        allowed, remaining, reset_at = await self._allow(identity)
        headers = {
            "RateLimit-Limit": str(settings.rate_limit_requests),
            "RateLimit-Remaining": str(max(0, remaining)),
            "RateLimit-Reset": str(reset_at),
        }
        if not allowed:
            headers["Retry-After"] = str(max(1, reset_at - int(time.time())))
            return ORJSONResponse(
                {"error": {"message_key": "rate_limit.exceeded"}},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
            )
        response = await call_next(request)
        response.headers.update(headers)
        return response

    def _identity(self, request: Request) -> str:
        auth = request.headers.get("Authorization") or request.headers.get("X-API-Key")
        if auth:
            return f"auth:{auth[-24:]}"
        return f"ip:{client_ip(request)}"

    async def _allow(self, identity: str) -> tuple[bool, int, int]:
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds
        now = int(time.time())
        reset_at = ((now // window) + 1) * window
        if redis_runtime.client:
            key = f"ravenstore:rate_limit:{identity}:{now // window}"
            count = int(await redis_runtime.client.incr(key))
            if count == 1:
                await redis_runtime.client.expire(key, window + 1)
            return count <= limit, limit - count, reset_at
        bucket = [stamp for stamp in self._memory[identity] if now - stamp < window]
        allowed = len(bucket) < limit
        if allowed:
            bucket.append(float(now))
        self._memory[identity] = bucket
        return allowed, limit - len(bucket), reset_at
