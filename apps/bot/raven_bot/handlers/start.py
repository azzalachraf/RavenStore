from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from raven_bot.api.client import RavenAPI
from raven_bot.domain import BotSession, TelegramIdentity
from raven_bot.handlers.common import respond
from raven_bot.i18n import i18n
from raven_bot.middlewares.session import SessionMiddleware
from raven_bot.ui import callbacks as cb
from raven_bot.ui.formatters import home_text, language_text
from raven_bot.ui.keyboards import home_keyboard, language_keyboard

router = Router()


@router.message(CommandStart())
async def start(message: Message, t) -> None:
    await message.answer(language_text(t), reply_markup=language_keyboard(t))


@router.callback_query(F.data == cb.HOME)
async def home(callback: CallbackQuery, t) -> None:
    await respond(callback, home_text(t), home_keyboard(t))


@router.callback_query(F.data == cb.LANG)
async def choose_language(callback: CallbackQuery, t) -> None:
    await respond(callback, language_text(t), language_keyboard(t))


@router.callback_query(F.data.startswith(f"{cb.LANG}:"))
async def save_language(
    callback: CallbackQuery,
    api: RavenAPI,
    identity: TelegramIdentity,
    bot_session: BotSession,
    session_middleware: SessionMiddleware,
    t,
) -> None:
    locale = callback.data.split(":", 1)[1]
    session = await api.save_language(bot_session.access_token, locale, identity)
    session_middleware.remember(identity.telegram_id, session)
    remote_catalog = await api.translations(locale)

    def local_t(key: str, **params):
        return i18n.t(key, locale, remote_catalog, **params)

    await callback.answer(local_t("language.saved"))
    await respond(callback, home_text(local_t), home_keyboard(local_t))
