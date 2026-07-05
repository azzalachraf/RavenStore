from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def respond(
    target: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if isinstance(target, CallbackQuery):
        await target.answer()
        if target.message:
            try:
                await target.message.edit_text(text, reply_markup=reply_markup)
                return
            except TelegramBadRequest:
                await target.message.answer(text, reply_markup=reply_markup)
                return
        return
    await target.answer(text, reply_markup=reply_markup)

