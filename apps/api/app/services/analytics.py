from __future__ import annotations

from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalyticsEvent, Category, Order, OrderItem, Payment, Product, TelegramUser, User


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def summary(self) -> dict:
        completed_statuses = ["paid", "fulfilling", "fulfilled", "completed"]
        revenue = await self._scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status.in_(completed_statuses)))
        cost = await self._scalar(select(func.coalesce(func.sum(Order.cost_amount), 0)).where(Order.status.in_(completed_statuses)))
        orders = await self._scalar(select(func.count(Order.id)))
        visitors = await self._scalar(select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.event_type == "visitor"))
        telegram_users = await self._scalar(select(func.count(TelegramUser.id)))
        website_users = await self._scalar(select(func.count(User.id)).where(User.email.is_not(None)))
        paid_orders = await self._scalar(select(func.count(Order.id)).where(Order.status.in_(completed_statuses)))
        conversion = Decimal(paid_orders or 0) / Decimal(visitors or 1)
        payment_rows = await self.session.execute(select(Payment.status, func.count(Payment.id)).group_by(Payment.status))
        return {
            "revenue": revenue,
            "profit": Decimal(revenue) - Decimal(cost),
            "orders": orders,
            "visitors": visitors,
            "telegram_users": telegram_users,
            "website_users": website_users,
            "best_selling_products": await self._best_selling_products(),
            "top_categories": await self._top_categories(),
            "conversion_rate": conversion,
            "payment_statistics": dict(payment_rows.all()),
        }

    async def _best_selling_products(self) -> list[dict]:
        result = await self.session.execute(
            select(Product.id, Product.name_key, func.sum(OrderItem.quantity).label("sold"))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id, Product.name_key)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
        )
        return [{"product_id": str(row.id), "name_key": row.name_key, "sold": int(row.sold)} for row in result.all()]

    async def _top_categories(self) -> list[dict]:
        result = await self.session.execute(
            select(Category.id, Category.name_key, func.count(distinct(OrderItem.order_id)).label("orders"))
            .join(Product, Product.category_id == Category.id)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Category.id, Category.name_key)
            .order_by(func.count(distinct(OrderItem.order_id)).desc())
            .limit(10)
        )
        return [{"category_id": str(row.id), "name_key": row.name_key, "orders": int(row.orders)} for row in result.all()]

    async def _scalar(self, statement):
        result = await self.session.execute(statement)
        return result.scalar_one()
