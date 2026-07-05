from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from raven_bot.api.client import RavenAPI
from raven_bot.config import settings
from raven_bot.domain import BotSession
from raven_bot.handlers.common import respond
from raven_bot.ui import callbacks as cb
from raven_bot.ui.formatters import orders_text, profile_text, referral_text, reseller_text
from raven_bot.ui.keyboards import orders_keyboard, reseller_keyboard, single_back_keyboard

router = Router()


@router.callback_query(F.data.startswith(f"{cb.ORDERS}:"))
async def orders(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    status = callback.data.split(":", 1)[1]
    rows = await api.orders(bot_session.access_token, None if status == "all" else status)
    await respond(callback, orders_text(rows, t), orders_keyboard(t))


@router.callback_query(F.data == cb.WALLET)
async def wallet(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    summary = await api.wallet(bot_session.access_token)
    await respond(callback, wallet_text(summary, t), single_back_keyboard(t))


@router.callback_query(F.data == cb.REFERRAL)
async def referral(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    stats = await api.referral_stats(bot_session.access_token, settings.bot_public_username)
    await respond(callback, referral_text(stats, t), single_back_keyboard(t))


@router.callback_query(F.data == cb.PROFILE)
async def profile(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    profile_data = await api.profile(bot_session.access_token)
    orders = await api.orders(bot_session.access_token)
    await respond(callback, profile_text(profile_data, orders, t), single_back_keyboard(t))


@router.callback_query(F.data == cb.API_KEY)
async def show_api_key(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    data = await api.get_api_key(bot_session.access_token)
    prefix = data.get("name") if data else None
    await respond(callback, reseller_text(None, prefix, t), reseller_keyboard(t))


@router.callback_query(F.data == cb.REGENERATE_API_KEY)
async def regenerate_api_key(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    data = await api.generate_api_key(bot_session.access_token)
    raw_key = data.get("api_key")
    prefix = data.get("name")
    await respond(callback, reseller_text(raw_key, prefix, t), reseller_keyboard(t))

