from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery

from raven_bot.api.client import RavenAPI
from raven_bot.handlers.common import respond
from raven_bot.runtime.navigation import navigation_cache
from raven_bot.ui import callbacks as cb
from raven_bot.ui.formatters import catalog_text, checkout_review, product_detail
from raven_bot.ui.keyboards import (
    catalog_keyboard,
    checkout_keyboard,
    product_keyboard,
)

router = Router()
PAGE_SIZE = 6


@router.callback_query(F.data.startswith(f"{cb.STORE}:"))
async def store(callback: CallbackQuery, api: RavenAPI, t) -> None:
    parts = callback.data.split(":")
    page = int(parts[1])
    products = await api.products(page=page, page_size=PAGE_SIZE)
    text = catalog_text(t, page)
    if not products:
        text = f"{text}\n\n{t('catalog.empty')}"
    await respond(callback, text, catalog_keyboard(products, page, t, cb.STORE))


@router.callback_query(F.data.startswith(f"{cb.PRODUCT}:"))
async def product(callback: CallbackQuery, api: RavenAPI, t) -> None:
    token = callback.data.split(":", 1)[1]
    slug = navigation_cache.get(token)
    if not slug:
        await callback.answer(t("error.navigation_expired"), show_alert=True)
        return
    item = await api.product(slug)
    text = product_detail(item, t)
    if item.images and callback.message:
        await callback.answer()
        await callback.message.answer_photo(item.images[0].url, caption=text, reply_markup=product_keyboard(item, t))
        return
    await respond(callback, text, product_keyboard(item, t))


@router.callback_query(F.data.startswith(f"{cb.BUY}:"))
async def buy(callback: CallbackQuery, api: RavenAPI, t) -> None:
    _, variant_id, product_token = callback.data.split(":")
    slug = navigation_cache.get(product_token)
    if not slug:
        await callback.answer(t("error.navigation_expired"), show_alert=True)
        return
    item = await api.product(slug)
    text = checkout_review(item, t)
    await respond(callback, text, checkout_keyboard(UUID(variant_id), product_token, t))

