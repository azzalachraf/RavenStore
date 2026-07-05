from __future__ import annotations

import asyncio
from contextlib import suppress

from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from raven_bot.api.client import RavenAPI
from raven_bot.bot_factory import create_bot, create_dispatcher
from raven_bot.config import settings
from raven_bot.logging import configure_logging, logger


async def run_polling() -> None:
    configure_logging()
    api = RavenAPI()
    bot = create_bot()
    dispatcher = create_dispatcher(api)
    event_task = asyncio.create_task(api.watch_events(), name="ravenstore-event-stream")
    try:
        logger.info("bot.polling.started")
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        event_task.cancel()
        with suppress(asyncio.CancelledError):
            await event_task
        await api.close()
        await bot.session.close()


async def run_webhook() -> None:
    configure_logging()
    if not settings.webhook_url:
        raise RuntimeError("WEBHOOK_BASE_URL is required in webhook mode")
    api = RavenAPI()
    bot = create_bot()
    dispatcher = create_dispatcher(api)
    app = web.Application()

    async def liveness(_: web.Request) -> web.Response:
        return web.json_response({"status": "alive"})

    async def readiness(_: web.Request) -> web.Response:
        healthy = await api.healthy()
        return web.json_response(
            {"status": "ready" if healthy else "not_ready", "api": "healthy" if healthy else "unavailable"},
            status=200 if healthy else 503,
        )

    app.router.add_get("/health/live", liveness)
    app.router.add_get("/health/ready", readiness)
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret_value,
    ).register(app, path=settings.webhook_path)
    setup_application(app, dispatcher, bot=bot)
    event_task: asyncio.Task | None = None

    async def on_startup(_: web.Application) -> None:
        nonlocal event_task
        logger.info("bot.webhook.setting", url=settings.webhook_url)
        await bot.set_webhook(
            settings.webhook_url,
            secret_token=settings.webhook_secret_value,
            drop_pending_updates=False,
        )
        event_task = asyncio.create_task(api.watch_events(), name="ravenstore-event-stream")

    async def on_cleanup(_: web.Application) -> None:
        if event_task:
            event_task.cancel()
            with suppress(asyncio.CancelledError):
                await event_task
        await api.close()
        await bot.session.close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    logger.info("bot.webhook.started", host=settings.web_server_host, port=settings.web_server_port)
    await web._run_app(app, host=settings.web_server_host, port=settings.web_server_port)


def main() -> None:
    if settings.bot_mode == "polling":
        asyncio.run(run_polling())
    else:
        asyncio.run(run_webhook())


if __name__ == "__main__":
    main()
