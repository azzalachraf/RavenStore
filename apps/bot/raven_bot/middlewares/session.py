from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from raven_bot.api.client import APIError
from raven_bot.api.client import RavenAPI
from raven_bot.config import settings
from raven_bot.domain import BotSession, TelegramIdentity
from raven_bot.i18n import i18n


class SessionMiddleware(BaseMiddleware):
    def __init__(self, api: RavenAPI):
        self.api = api
        self._cache: dict[int, tuple[float, BotSession]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        identity = self._identity(event)
        session = await self._session(identity)
        remote_catalog = await self.api.translations(session.locale)
        data["api"] = self.api
        data["session_middleware"] = self
        data["identity"] = identity
        data["bot_session"] = session
        data["locale"] = session.locale
        data["remote_catalog"] = remote_catalog
        data["t"] = lambda key, **params: i18n.t(key, session.locale, remote_catalog, **params)
        return await handler(event, data)

    async def _session(self, identity: TelegramIdentity) -> BotSession:
        cached = self._cache.get(identity.telegram_id)
        if cached and time.time() - cached[0] < 60:
            return cached[1]
        try:
            session = await self.api.bootstrap_session(identity)
        except APIError:
            session = BotSession(locale=identity.language_code or settings.default_locale)
        if not session.locale:
            session.locale = identity.language_code or settings.default_locale
        self._cache[identity.telegram_id] = (time.time(), session)
        return session

    def remember(self, telegram_id: int, session: BotSession) -> None:
        self._cache[telegram_id] = (time.time(), session)

    def _identity(self, event: TelegramObject) -> TelegramIdentity:
        source = event
        referral_code = None
        if isinstance(event, Message):
            source = event
            if event.text and event.text.startswith("/start "):
                referral_code = event.text.split(maxsplit=1)[1]
        elif isinstance(event, CallbackQuery):
            source = event.message or event
        user = getattr(event, "from_user", None) or getattr(source, "from_user", None)
        return TelegramIdentity(
            telegram_id=user.id if user else 0,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
            last_name=user.last_name if user else None,
            language_code=user.language_code if user else settings.default_locale,
            referral_code=referral_code,
        )
