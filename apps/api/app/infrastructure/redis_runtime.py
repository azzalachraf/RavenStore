from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import logger


class RedisRuntime:
    def __init__(self) -> None:
        self.client: Redis | None = None
        self._local_subscribers: set[asyncio.Queue[tuple[str, dict[str, Any]]]] = set()
        self._local_sequence = 0

    @property
    def available(self) -> bool:
        return self.client is not None

    async def connect(self) -> None:
        if not settings.redis_url:
            if settings.environment.lower() == "production":
                raise RuntimeError("REDIS_URL is required in production")
            logger.warning("redis.disabled", fallback="in_process")
            return
        client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await client.ping()
        self.client = client
        logger.info("redis.connected")

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None

    async def ping(self) -> bool:
        if self.client is None:
            return settings.environment.lower() != "production"
        try:
            return bool(await self.client.ping())
        except Exception:
            return False

    async def publish_event(self, envelope: dict[str, Any]) -> str:
        body = json.dumps(envelope, separators=(",", ":"), default=str)
        if self.client:
            stream_id = await self.client.xadd(
                settings.event_stream_name,
                {"event": body},
                maxlen=settings.event_stream_max_length,
                approximate=True,
            )
            await self.client.hincrby("ravenstore:metrics:events", "published_total", 1)
            return str(stream_id)
        self._local_sequence += 1
        stream_id = f"{self._local_sequence}-0"
        for queue in list(self._local_subscribers):
            queue.put_nowait((stream_id, envelope))
        return stream_id

    async def stream(self, last_id: str = "$") -> AsyncIterator[tuple[str | None, dict[str, Any] | None]]:
        if self.client:
            cursor = last_id if _valid_stream_id(last_id) else "$"
            if cursor == "$":
                latest = await self.client.xrevrange(settings.event_stream_name, count=1)
                cursor = str(latest[0][0]) if latest else "0-0"
            while True:
                rows = await self.client.xread(
                    {settings.event_stream_name: cursor},
                    count=100,
                    block=settings.event_sse_heartbeat_seconds * 1000,
                )
                if not rows:
                    yield None, None
                    continue
                for _, messages in rows:
                    for stream_id, fields in messages:
                        cursor = str(stream_id)
                        yield cursor, json.loads(fields["event"])
            return
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=1000)
        self._local_subscribers.add(queue)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=settings.event_sse_heartbeat_seconds)
                except TimeoutError:
                    yield None, None
        finally:
            self._local_subscribers.discard(queue)

    async def invalidate(self, tags: list[str]) -> None:
        if not self.client or not tags:
            return
        pipeline = self.client.pipeline(transaction=False)
        for tag in tags:
            pipeline.incr(f"{settings.cache_prefix}:tag:{tag}")
        pipeline.hincrby("ravenstore:metrics:cache", "invalidations_total", len(tags))
        await pipeline.execute()

    async def cache_key(self, raw_key: str, tags: list[str]) -> str:
        versions = ["0"] * len(tags)
        if self.client and tags:
            values = await self.client.mget([f"{settings.cache_prefix}:tag:{tag}" for tag in tags])
            versions = [str(value or 0) for value in values]
        version_key = ":".join(f"{tag}={version}" for tag, version in zip(tags, versions, strict=True))
        digest = hashlib.sha256(f"{raw_key}|{version_key}".encode()).hexdigest()
        return f"{settings.cache_prefix}:response:{digest}"

    async def cache_get(self, key: str) -> dict[str, Any] | None:
        if not self.client:
            return None
        value = await self.client.get(key)
        if value is None:
            await self.client.hincrby("ravenstore:metrics:cache", "misses_total", 1)
            return None
        await self.client.hincrby("ravenstore:metrics:cache", "hits_total", 1)
        return json.loads(value)

    async def cache_set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        if self.client:
            await self.client.setex(
                key,
                ttl or settings.cache_default_ttl_seconds,
                json.dumps(value, separators=(",", ":"), default=str),
            )

    async def metrics(self) -> dict[str, dict[str, int | float]]:
        if not self.client:
            return {"events": {}, "cache": {}, "http": {}}
        events = await self.client.hgetall("ravenstore:metrics:events")
        cache = await self.client.hgetall("ravenstore:metrics:cache")
        http = await self.client.hgetall("ravenstore:metrics:http")
        return {
            "events": {key: int(value) for key, value in events.items()},
            "cache": {key: int(value) for key, value in cache.items()},
            "http": {key: float(value) if "." in value else int(value) for key, value in http.items()},
        }

    async def record_request(self, *, status_code: int, duration_ms: float) -> None:
        if not self.client:
            return
        pipeline = self.client.pipeline(transaction=False)
        pipeline.hincrby("ravenstore:metrics:http", "requests_total", 1)
        pipeline.hincrby("ravenstore:metrics:http", f"status_{status_code // 100}xx", 1)
        pipeline.hincrbyfloat("ravenstore:metrics:http", "duration_ms_total", duration_ms)
        bucket = "le_100ms" if duration_ms <= 100 else "le_500ms" if duration_ms <= 500 else "le_1000ms" if duration_ms <= 1000 else "gt_1000ms"
        pipeline.hincrby("ravenstore:metrics:http", bucket, 1)
        await pipeline.execute()

    async def heartbeat(self, worker: str) -> None:
        if self.client:
            await self.client.setex(
                f"ravenstore:workers:heartbeat:{worker}",
                settings.worker_heartbeat_ttl_seconds,
                str(int(time.time())),
            )

    async def worker_health(self, workers: list[str]) -> dict[str, str]:
        if not self.client:
            fallback = "development" if settings.environment.lower() != "production" else "unavailable"
            return {worker: fallback for worker in workers}
        values = await self.client.mget([f"ravenstore:workers:heartbeat:{worker}" for worker in workers])
        return {worker: "healthy" if value else "stale" for worker, value in zip(workers, values, strict=True)}


def _valid_stream_id(value: str) -> bool:
    if value in {"$", "0", "0-0"}:
        return True
    parts = value.split("-", 1)
    return len(parts) == 2 and all(part.isdigit() for part in parts)


redis_runtime = RedisRuntime()
