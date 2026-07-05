from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis

from raven_bot.config import settings


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis | None = None):
        self.limit = settings.throttle_limit
        self.window_seconds = settings.throttle_window_seconds
        self.bucket: dict[int, list[float]] = defaultdict(list)
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)
        allowed = await self._allow(user.id)
        if not allowed:
            t = data.get("t")
            text = t("error.rate_limited") if t else "error.rate_limited"
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=False)
            elif isinstance(event, Message):
                await event.answer(text)
            return None
        return await handler(event, data)

    async def _allow(self, user_id: int) -> bool:
        now = int(time.time())
        if self.redis:
            key = f"ravenstore:bot:throttle:{user_id}:{now // self.window_seconds}"
            count = int(await self.redis.incr(key))
            if count == 1:
                await self.redis.expire(key, self.window_seconds + 1)
            return count <= self.limit
        hits = [stamp for stamp in self.bucket[user_id] if now - stamp < self.window_seconds]
        if len(hits) >= self.limit:
            self.bucket[user_id] = hits
            return False
        hits.append(float(now))
        self.bucket[user_id] = hits
        return True
