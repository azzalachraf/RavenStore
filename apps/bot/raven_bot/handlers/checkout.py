from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from raven_bot.api.client import RavenAPI
from raven_bot.domain import BotSession
from raven_bot.runtime.navigation import navigation_cache
from raven_bot.states import CheckoutStates
from raven_bot.ui import callbacks as cb
from raven_bot.ui.formatters import payment_instructions
from raven_bot.ui.keyboards import payment_methods_keyboard, submit_payment_keyboard

router = Router()


@router.callback_query(F.data.startswith(f"{cb.CHECKOUT_CONFIRM}:"))
async def create_order(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    _, variant_id, _ = callback.data.split(":")
    order = await api.create_order(bot_session.access_token, UUID(variant_id))
    await callback.answer(t("checkout.order_created"))
    if callback.message:
        await callback.message.edit_text(
            f"<b>{t('checkout.title')}</b>\n\n{t('checkout.payment_method')}",
            reply_markup=payment_methods_keyboard(order.id, t),
        )


@router.callback_query(F.data.startswith(f"{cb.PAYMENT_METHOD}:"))
async def payment_method(callback: CallbackQuery, api: RavenAPI, bot_session: BotSession, t) -> None:
    _, method, order_id = callback.data.split(":")
    payment = await api.request_payment(bot_session.access_token, UUID(order_id), method)
    text = payment_instructions(
        payment.payment.amount,
        payment.payment.currency,
        payment.payment.payment_address,
        t,
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=submit_payment_keyboard(payment.payment_token, t))
    await callback.answer()


@router.callback_query(F.data.startswith(f"{cb.SUBMIT_PAYMENT}:"))
async def submit_payment_prompt(callback: CallbackQuery, state: FSMContext, t) -> None:
    token_key = callback.data.split(":", 1)[1]
    payment_token = navigation_cache.get(token_key)
    if not payment_token:
        await callback.answer(t("error.navigation_expired"), show_alert=True)
        return
    await state.set_state(CheckoutStates.waiting_payment_id)
    await state.update_data(payment_token=payment_token)
    if callback.message:
        await callback.message.edit_text(f"<b>{t('checkout.title')}</b>\n\n{t('checkout.enter_payment_id')}")
    await callback.answer()


@router.message(CheckoutStates.waiting_payment_id)
async def submit_payment_id(message: Message, state: FSMContext, api: RavenAPI, t) -> None:
    data = await state.get_data()
    await state.clear()
    await api.submit_payment_verification(data["payment_token"], message.text or "")
    await message.answer(t("checkout.verification_sent"))

