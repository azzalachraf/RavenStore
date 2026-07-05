from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.redis_runtime import redis_runtime
from app.core.network import client_ip_hash
from app.core.observability import observe_http
logger = structlog.get_logger("ravenstore.requests")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        start = perf_counter()
        response = await call_next(request)
        duration_seconds = perf_counter() - start
        duration_ms = round(duration_seconds * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip_hash=client_ip_hash(request),
        )
        route = request.scope.get("route")
        observe_http(request.method, getattr(route, "path", request.url.path), response.status_code, duration_seconds)
        if duration_ms > 1000:
            logger.warning(
                "request.slow",
                method=request.method,
                duration_ms=duration_ms,
                status_code=response.status_code,
            )
        try:
            await redis_runtime.record_request(status_code=response.status_code, duration_ms=duration_ms)
        except Exception as exc:
            logger.warning("metrics.record_failed", error=str(exc))
        structlog.contextvars.clear_contextvars()
        return response
