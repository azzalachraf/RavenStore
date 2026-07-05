from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalyticsDailyMetric, AnalyticsEvent, DeliveryQueue, InventoryAsset, Order, Payment


class AnalyticsWorker:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def aggregate_today(self) -> None:
        today = date.today()
        start = datetime(today.year, today.month, today.day, tzinfo=UTC)
        revenue = await self.session.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.created_at >= start,
                Order.status.in_(["paid", "fulfilling", "completed"]),
            )
        )
        orders = await self.session.scalar(select(func.count(Order.id)).where(Order.created_at >= start))
        payment_counts = (
            await self.session.execute(
                select(
                    func.count(Payment.id),
                    func.sum(case((Payment.status == "confirmed", 1), else_=0)),
                    func.sum(case((Payment.status.in_(["failed", "expired"]), 1), else_=0)),
                ).where(Payment.created_at >= start)
            )
        ).one()
        total_payments = int(payment_counts[0] or 0)
        confirmed = int(payment_counts[1] or 0)
        failed = int(payment_counts[2] or 0)
        abandoned = await self.session.scalar(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.created_at >= start,
                AnalyticsEvent.event_type == "checkout.abandoned",
            )
        )
        average_order_value = await self.session.scalar(
            select(func.coalesce(func.avg(Order.total_amount), 0)).where(
                Order.created_at >= start,
                Order.status.in_(["paid", "fulfilling", "completed"]),
            )
        )
        average_delivery_seconds = await self.session.scalar(
            select(func.coalesce(func.avg(func.extract("epoch", DeliveryQueue.completed_at - DeliveryQueue.created_at)), 0)).where(
                DeliveryQueue.completed_at.is_not(None),
                DeliveryQueue.created_at >= start,
            )
        )
        delivered_inventory = await self.session.scalar(
            select(func.count(InventoryAsset.id)).where(
                InventoryAsset.status == "delivered",
                InventoryAsset.delivered_at >= start,
            )
        )
        available_inventory = await self.session.scalar(
            select(func.count(InventoryAsset.id)).where(InventoryAsset.status == "available")
        )
        success_rate = Decimal(confirmed * 100) / Decimal(total_payments) if total_payments else Decimal("0")
        metrics = {
            "revenue": revenue or 0,
            "orders": orders or 0,
            "payment_success_rate": success_rate,
            "failed_payments": failed,
            "abandoned_checkouts": abandoned or 0,
            "average_order_value": average_order_value or 0,
            "average_delivery_seconds": average_delivery_seconds or 0,
            "inventory_delivered": delivered_inventory or 0,
            "inventory_available": available_inventory or 0,
        }
        for key, value in metrics.items():
            await self._upsert(today, key, value)
        await self.session.commit()

    async def _upsert(self, metric_date: date, metric_key: str, value) -> None:
        statement = insert(AnalyticsDailyMetric).values(
            metric_date=metric_date,
            metric_key=metric_key,
            value=value,
            metric_metadata={},
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_metric_date_key",
            set_={"value": value, "updated_at": datetime.now(UTC)},
        )
        await self.session.execute(statement)
