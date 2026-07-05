from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from raven_bot.api.client import APIError, RavenAPI
from raven_bot.logging import logger


class TelemetryMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        api: RavenAPI | None = data.get("api")
        session = data.get("bot_session")
        event_type = self._event_type(event)
        try:
            result = await handler(event, data)
            if api and event_type:
                await api.analytics_event(getattr(session, "access_token", None), event_type, self._metadata(event))
            return result
        except APIError as exc:
            logger.warning("api.error", message_key=exc.message_key, status_code=exc.status_code)
            t = data.get("t")
            text = t(exc.message_key) if t else exc.message_key
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(text)
        except Exception as exc:
            logger.exception("handler.failed", error=str(exc))
            t = data.get("t")
            text = t("error.unexpected") if t else "error.unexpected"
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(text)

    def _event_type(self, event: TelegramObject) -> str | None:
        if isinstance(event, Message):
            if event.text and event.text.startswith("/start"):
                return "telegram.start"
            return "telegram.message"
        if isinstance(event, CallbackQuery):
            return f"telegram.callback.{event.data.split(':', 1)[0]}" if event.data else "telegram.callback"
        return None

    def _metadata(self, event: TelegramObject) -> dict[str, str | int | None]:
        if isinstance(event, CallbackQuery):
            return {"callback": event.data, "telegram_id": event.from_user.id}
        if isinstance(event, Message):
            return {"telegram_id": event.from_user.id, "message_type": event.content_type}
        return {}

