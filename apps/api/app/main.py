from __future__ import annotations

from contextlib import asynccontextmanager

import secrets

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.network import is_allowlisted
from app.core.observability import prometheus_payload
from app.core.tracing import configure_tracing
from app.infrastructure.redis_runtime import redis_runtime
from sqlalchemy import text
from app.middleware.audit import RequestContextMiddleware
from app.middleware.cache import PublicCacheMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await redis_runtime.connect()
    try:
        yield
    finally:
        await redis_runtime.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json" if settings.api_docs_enabled else None,
    docs_url=f"{settings.api_v1_prefix}/docs" if settings.api_docs_enabled else None,
    redoc_url=f"{settings.api_v1_prefix}/redoc" if settings.api_docs_enabled else None,
    lifespan=lifespan,
)
configure_tracing(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID", "X-API-Key", "X-Request-ID"],
    expose_headers=["ETag", "RateLimit-Limit", "RateLimit-Remaining", "RateLimit-Reset", "Retry-After", "X-Request-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.upload_max_bytes + 1024 * 1024)
app.add_middleware(PublicCacheMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RequestContextMiddleware)

install_error_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ravenstore-api"}


@app.get("/health/ready", tags=["system"])
async def readiness_check():
    database_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            database_ok = True
    except Exception:
        database_ok = False
    redis_ok = await redis_runtime.ping()
    ready = database_ok and redis_ok
    return ORJSONResponse({
        "status": "ready" if ready else "not_ready",
        "database": "healthy" if database_ok else "unavailable",
        "redis": "healthy" if redis_ok else "unavailable",
    }, status_code=200 if ready else 503)


@app.get("/health/live", tags=["system"])
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/metrics", include_in_schema=False)
async def metrics(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Response:
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    token_valid = bool(settings.metrics_bearer_token) and secrets.compare_digest(supplied, settings.metrics_bearer_token)
    if not token_valid and not is_allowlisted(request):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="auth.forbidden")
    return Response(prometheus_payload(), media_type="text/plain; version=0.0.4; charset=utf-8")
