from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.redis_runtime import redis_runtime


class PublicCacheMiddleware(BaseHTTPMiddleware):
    ROUTES: tuple[tuple[str, list[str], int], ...] = (
        ("/api/v1/products", ["products", "inventory"], 60),
        ("/api/v1/categories", ["categories"], 120),
        ("/api/v1/languages", ["languages", "translations"], 120),
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        route = self._route(request)
        if request.method != "GET" or route is None or request.headers.get("Authorization"):
            return await call_next(request)
        _, tags, ttl = route
        raw_key = f"{request.url.path}?{request.url.query}|{request.headers.get('Accept-Language', '')}"
        key = await redis_runtime.cache_key(raw_key, tags)
        cached = await redis_runtime.cache_get(key)
        if cached:
            etag = cached["etag"]
            if request.headers.get("If-None-Match") == etag:
                return Response(status_code=304, headers={"ETag": etag, "X-Cache": "HIT"})
            return Response(
                content=cached["body"].encode(),
                status_code=cached["status"],
                media_type=cached["content_type"],
                headers={"ETag": etag, "X-Cache": "HIT", "Cache-Control": f"public, max-age=0, s-maxage={ttl}"},
            )
        response = await call_next(request)
        if response.status_code != 200:
            return response
        chunks = [chunk async for chunk in response.body_iterator]
        body = b"".join(chunks)
        etag = f'"{hashlib.sha256(body).hexdigest()}"'
        content_type = response.media_type or response.headers.get("content-type", "application/json").split(";", 1)[0]
        await redis_runtime.cache_set(
            key,
            {"body": body.decode(), "status": response.status_code, "content_type": content_type, "etag": etag},
            ttl,
        )
        headers = dict(response.headers)
        headers.update({"ETag": etag, "X-Cache": "MISS", "Cache-Control": f"public, max-age=0, s-maxage={ttl}"})
        return Response(content=body, status_code=response.status_code, headers=headers, media_type=content_type)

    def _route(self, request: Request) -> tuple[str, list[str], int] | None:
        for route in self.ROUTES:
            if request.url.path == route[0] or request.url.path.startswith(f"{route[0]}/"):
                return route
        return None
