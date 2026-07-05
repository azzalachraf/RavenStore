from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raven_bot.handlers.common import respond
from raven_bot.ui import callbacks as cb

router = Router()


@router.callback_query(F.data == cb.SUPPORT)
async def support_home(callback: CallbackQuery, t) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="📩 Telegram Support", url="https://t.me/raven_store_support")
    builder.button(text=t("back"), callback_data=cb.HOME)
    builder.adjust(1)
    await respond(callback, t("support.text"), builder.as_markup())

