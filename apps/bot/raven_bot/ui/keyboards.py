from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from raven_bot.domain import Category, Product
from raven_bot.runtime.navigation import navigation_cache
from raven_bot.ui import callbacks as cb
from raven_bot.ui.formatters import primary_variant

T = Callable[..., str]


def language_keyboard(t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("language.english"), callback_data=f"{cb.LANG}:en")
    builder.button(text=t("language.arabic"), callback_data=f"{cb.LANG}:ar")
    builder.adjust(1)
    return builder.as_markup()


def home_keyboard(t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("home.store"), callback_data=f"{cb.STORE}:1")
    builder.button(text=t("home.profile"), callback_data=cb.PROFILE)
    builder.button(text=t("home.orders"), callback_data=f"{cb.ORDERS}:all")
    builder.button(text=t("home.referral"), callback_data=cb.REFERRAL)
    builder.button(text=t("home.reseller"), callback_data=cb.API_KEY)
    builder.button(text=t("home.support"), callback_data=cb.SUPPORT)
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def catalog_keyboard(products: list[Product], page: int, t: T, scope: str = cb.STORE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        token = navigation_cache.put(product.slug)
        builder.button(text=t(product.name_key), callback_data=f"{cb.PRODUCT}:{token}")
    builder.adjust(1)
    
    nav_builder = InlineKeyboardBuilder()
    if page > 1:
        nav_builder.button(text=t("previous"), callback_data=f"{scope}:{page - 1}")
    if len(products) >= 6:
        nav_builder.button(text=t("next"), callback_data=f"{scope}:{page + 1}")
    nav_builder.adjust(2 if (page > 1 and len(products) >= 6) else 1)
    
    builder.attach(nav_builder)
    
    back_builder = InlineKeyboardBuilder()
    back_builder.button(text=t("back"), callback_data=cb.HOME)
    builder.attach(back_builder)
    
    return builder.as_markup()


def category_keyboard(categories: list[Category], t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=t(category.name_key), callback_data=f"{cb.CATEGORY}:{category.id}:1")
    builder.button(text=t("back"), callback_data=cb.HOME)
    builder.adjust(1)
    return builder.as_markup()


def filters_keyboard(t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("catalog.featured"), callback_data=f"{cb.FEATURED}:1")
    builder.button(text=t("catalog.popular"), callback_data=f"{cb.STORE}:1:popular")
    builder.button(text=t("catalog.new"), callback_data=f"{cb.STORE}:1:new")
    builder.button(text=t("catalog.categories"), callback_data=cb.CATEGORIES)
    builder.button(text=t("back"), callback_data=f"{cb.STORE}:1")
    builder.adjust(1)
    return builder.as_markup()


def product_keyboard(product: Product, t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    variant = primary_variant(product)
    if variant:
        builder.button(text=t("product.buy"), callback_data=f"{cb.BUY}:{variant.id}:{navigation_cache.put(product.slug)}")
    builder.button(text=t("back"), callback_data=f"{cb.STORE}:1")
    builder.adjust(1)
    return builder.as_markup()


def checkout_keyboard(variant_id: UUID, product_token: str, t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("checkout.create_order"), callback_data=f"{cb.CHECKOUT_CONFIRM}:{variant_id}:{product_token}")
    builder.button(text=t("cancel"), callback_data=f"{cb.PRODUCT}:{product_token}")
    builder.adjust(1)
    return builder.as_markup()


def payment_methods_keyboard(order_id: UUID, t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("checkout.binance"), callback_data=f"{cb.PAYMENT_METHOD}:binance:{order_id}")
    builder.button(text=t("checkout.usdt_trc20"), callback_data=f"{cb.PAYMENT_METHOD}:usdt_trc20:{order_id}")
    builder.button(text=t("checkout.usdt_bep20"), callback_data=f"{cb.PAYMENT_METHOD}:usdt_bep20:{order_id}")
    builder.button(text=t("back"), callback_data=cb.HOME)
    builder.adjust(1)
    return builder.as_markup()


def submit_payment_keyboard(payment_token: str, t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    token = navigation_cache.put(payment_token)
    builder.button(text=t("checkout.submit_id"), callback_data=f"{cb.SUBMIT_PAYMENT}:{token}")
    builder.button(text=t("home.orders"), callback_data=f"{cb.ORDERS}:all")
    builder.adjust(1)
    return builder.as_markup()


def orders_keyboard(t: T) -> InlineKeyboardMarkup:
    return single_back_keyboard(t)


def support_keyboard(t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("support.new_ticket"), callback_data=cb.SUPPORT_NEW)
    builder.button(text=t("support.my_tickets"), callback_data=cb.SUPPORT_LIST)
    builder.button(text=t("back"), callback_data=cb.HOME)
    builder.adjust(1)
    return builder.as_markup()


def reseller_keyboard(t: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("reseller.regenerate"), callback_data=cb.REGENERATE_API_KEY)
    builder.button(text=t("back"), callback_data=cb.HOME)
    builder.adjust(1)
    return builder.as_markup()


def single_back_keyboard(t: T, target: str = cb.HOME) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data=target)]])

