from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Callable

from raven_bot.config import settings
from raven_bot.domain import Order, Product, ProductVariant, ReferralStats, WalletSummary

T = Callable[..., str]


def money(amount: Decimal, currency: str) -> str:
    return f"{amount:.2f} {currency}"


def home_text(t: T) -> str:
    return f"<b>{t('home.title')}</b>\n{escape(t('home.subtitle'))}"


def language_text(t: T) -> str:
    return f"<b>◆ {escape(t('language.title'))}</b>\n\n{escape(t('language.subtitle'))}"


def catalog_text(t: T, page: int) -> str:
    return f"<b>{t('catalog.title')}</b>\n{escape(t('catalog.subtitle'))}\n\n<b>{escape(t('catalog.page', page=page))}</b>"


def product_line(product: Product, t: T) -> str:
    variant = primary_variant(product)
    price = money(variant.price_amount, variant.currency) if variant else t("product.unavailable")
    return f"<b>{escape(t(product.name_key))}</b>\n{escape(price)}"


def stock_status(variant: ProductVariant | None, t: T) -> str:
    if not variant:
        return t("product.out_stock")
    if variant.unlimited_stock:
        return t("product.in_stock")
    if variant.stock_available is not None and variant.stock_available > 0:
        return t("product.in_stock")
    return t("product.out_stock")


def product_detail(product: Product, t: T) -> str:
    variant = primary_variant(product)
    duration = _duration(variant, t)
    price = money(variant.price_amount, variant.currency) if variant else t("product.unavailable")
    stock = stock_status(variant, t)
    description = t(product.description_key) if product.description_key else ""
    lines = [
        f"<b>{escape(t(product.name_key))}</b>",
        "",
        escape(description) if description else "",
        "",
        f"⏱ <b>{escape(t('product.duration'))}:</b> {escape(duration)}",
        f"💳 <b>{escape(t('product.price'))}:</b> {escape(price)}",
        f"📦 <b>{escape(t('product.stock'))}:</b> {escape(stock)}",
    ]
    return "\n".join([line for line in lines if line is not None]).strip()


def checkout_review(product: Product, t: T) -> str:
    variant = primary_variant(product)
    price = money(variant.price_amount, variant.currency) if variant else t("product.unavailable")
    return f"<b>{escape(t('checkout.title'))}</b>\n\n{escape(t('checkout.review'))}\n\n<b>{escape(t(product.name_key))}</b>\n💳 {escape(price)}"


def payment_instructions(amount: Decimal, currency: str, address: str | None, t: T) -> str:
    lines = [f"<b>{escape(t('checkout.title'))}</b>", "", escape(t("checkout.instructions", amount=amount, currency=currency))]
    if address:
        lines.append(f"<code>{escape(address)}</code>")
    lines.append("")
    lines.append(escape(t("checkout.enter_payment_id")))
    return "\n".join(lines)


def orders_text(orders: list[Order], t: T) -> str:
    if not orders:
        return f"<b>{t('orders.title')}</b>\n\n{t('orders.empty')}"
    lines = [f"<b>{t('orders.title')}</b>", ""]
    for order in orders:
        status_icon = _status_icon(order.status)
        price = money(order.total_amount, order.currency)
        date = order.created_at[:10] if order.created_at else t("unknown")
        lines.append(f"{status_icon} <b>{escape(order.order_number)}</b>")
        lines.append(f"└ {t('orders.date')}: {date} · {price} · {escape(order.status.capitalize())}")
        lines.append("")
    return "\n".join(lines).strip()


def wallet_text(summary: WalletSummary, t: T) -> str:
    return f"<b>{t('wallet.title')}</b>\n\n{t('wallet.summary', purchases=summary.purchase_count, balance=summary.future_balance, currency=summary.currency)}"


def referral_text(stats: ReferralStats, t: T) -> str:
    link = stats.link or f"https://t.me/{settings.bot_public_username}"
    total_invited = stats.invited_count
    successful_referrals = len([u for u in stats.invited_users if u.get("status") == "rewarded"])
    earnings = stats.reward_amount
    available_balance = earnings
    
    lines = [
        f"<b>{t('referral.title')}</b>",
        "",
        f"🔗 <b>{t('referral.link')}:</b>\n<code>{escape(link)}</code>",
        "",
        f"• <b>{t('referral.total_invited')}:</b> {total_invited}",
        f"• <b>{t('referral.successful')}:</b> {successful_referrals}",
        f"• <b>{t('referral.earnings')}:</b> {escape(money(earnings, 'USD'))}",
        f"• <b>{t('referral.balance')}:</b> {escape(money(available_balance, 'USD'))}",
    ]
    return "\n".join(lines)


def profile_text(profile_data: dict, orders: list[Order], t: T) -> str:
    first_name = profile_data.get("first_name") or ""
    last_name = profile_data.get("last_name") or ""
    name = f"{first_name} {last_name}".strip() or t("unknown")
    username = f"@{profile_data.get('username')}" if profile_data.get("username") else t("unknown")
    telegram_id = profile_data.get("telegram_id") or t("unknown")
    
    completed_orders = [o for o in orders if o.status.lower() in {"completed", "paid", "fulfilled"}]
    total_spent = sum(o.total_amount for o in completed_orders)
    
    lines = [
        f"<b>👤 {t('profile.title')}</b>",
        "",
        f"👤 <b>{t('profile.name')}:</b> {escape(name)}",
        f"🏷️ <b>{t('profile.username')}:</b> {escape(username)}",
        f"🆔 <b>{t('profile.id')}:</b> <code>{telegram_id}</code>",
        f"📦 <b>{t('profile.total_orders')}:</b> {len(orders)}",
        f"💰 <b>{t('profile.spent')}:</b> {escape(money(total_spent, 'USD'))}",
    ]
    return "\n".join(lines)


def primary_variant(product: Product) -> ProductVariant | None:
    for variant in product.variants:
        if variant.is_active:
            return variant
    return product.variants[0] if product.variants else None


def _duration(variant: ProductVariant | None, t: T) -> str:
    if not variant or not variant.duration_days:
        return t("product.instant")
    return t("product.duration_days", days=variant.duration_days)


def _stock(variant: ProductVariant | None, metadata: dict, t: T) -> str:
    if variant and variant.unlimited_stock:
        return t("product.stock_unlimited")
    count = variant.stock_available if variant and variant.stock_available is not None else metadata.get("stock")
    if count is None:
        return t("product.stock_unknown")
    return t("product.stock_value", count=count)


def _warranty(metadata: dict, t: T) -> str:
    days = metadata.get("warranty_days")
    if not days:
        return t("product.instant")
    return t("product.warranty_value", days=days)


def _status_icon(status: str) -> str:
    normalized = status.lower()
    if "complete" in normalized or "paid" in normalized:
        return "✅"
    if "fail" in normalized or "cancel" in normalized:
        return "⚠️"
    if "active" in normalized or "fulfill" in normalized:
        return "🟢"
    return "⏳"


def reseller_text(raw_key: str | None, prefix: str | None, t: T) -> str:
    key_display = raw_key if raw_key else (prefix if prefix else t("reseller.not_generated"))
    lines = [
        f"<b>🔗 {t('home.reseller')}</b>",
        "",
        f"🔑 <b>{t('reseller.key_label')}:</b>",
        f"<code>{escape(key_display)}</code>",
        "",
        f"📖 <b>{t('reseller.docs_label')}:</b>",
        "https://api.ravenstore.com/docs",
        "",
        f"⚠️ <i>{t('reseller.warning')}</i>"
    ]
    return "\n".join(lines)
