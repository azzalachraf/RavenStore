from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from raven_bot.api.client import RavenAPI
from raven_bot.config import settings
from raven_bot.handlers import account, catalog, checkout, start, support
from raven_bot.middlewares.session import SessionMiddleware
from raven_bot.middlewares.telemetry import TelemetryMiddleware
from raven_bot.middlewares.throttle import ThrottleMiddleware


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token_value,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(api: RavenAPI) -> Dispatcher:
    redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    storage = RedisStorage(redis) if redis else MemoryStorage()
    dispatcher = Dispatcher(storage=storage)
    session_middleware = SessionMiddleware(api)
    throttle_middleware = ThrottleMiddleware(redis)
    telemetry_middleware = TelemetryMiddleware()
    dispatcher.message.outer_middleware(session_middleware)
    dispatcher.callback_query.outer_middleware(session_middleware)
    dispatcher.message.outer_middleware(throttle_middleware)
    dispatcher.callback_query.outer_middleware(throttle_middleware)
    dispatcher.message.outer_middleware(telemetry_middleware)
    dispatcher.callback_query.outer_middleware(telemetry_middleware)
    dispatcher.include_router(start.router)
    dispatcher.include_router(catalog.router)
    dispatcher.include_router(checkout.router)
    dispatcher.include_router(account.router)
    dispatcher.include_router(support.router)
    return dispatcher
