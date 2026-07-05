from __future__ import annotations

import secrets
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Order, OrderItem, ProductVariant
from app.schemas.orders import OrderCreate
from app.services.audit import AuditService
from app.services.configuration import ConfigurationService
from app.services.inventory import InventoryService
from app.services.outbox import OutboxService


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditService(session)
        self.configuration = ConfigurationService(session)
        self.inventory = InventoryService(session)
        self.outbox = OutboxService(session)

    async def create_order(self, *, user_id: UUID, payload: OrderCreate) -> Order:
        variants: list[ProductVariant] = []
        variant_map = {item.product_variant_id: item.quantity for item in payload.items}
        result = await self.session.execute(select(ProductVariant).where(ProductVariant.id.in_(variant_map.keys()), ProductVariant.is_active.is_(True)))
        variants = list(result.scalars().all())
        if len(variants) != len(variant_map):
            raise AppError("variants.not_found", status.HTTP_404_NOT_FOUND)

        subtotal = Decimal("0")
        cost = Decimal("0")
        currency = variants[0].currency
        order = Order(
            order_number=self._order_number(),
            user_id=user_id,
            status="pending_payment",
            subtotal_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("0"),
            cost_amount=Decimal("0"),
            currency=currency,
        )
        self.session.add(order)
        await self.session.flush()

        automation = await self.configuration.automation()
        for variant in variants:
            quantity = variant_map[variant.id]
            subtotal += variant.price_amount * quantity
            cost += variant.cost_amount * quantity
            item = OrderItem(
                order_id=order.id,
                product_id=variant.product_id,
                product_variant_id=variant.id,
                quantity=quantity,
                unit_price_amount=variant.price_amount,
                unit_cost_amount=variant.cost_amount,
                snapshot={
                    "sku": variant.sku,
                    "name_key": variant.name_key,
                    "delivery_type": variant.delivery_type,
                    "currency": variant.currency,
                },
            )
            self.session.add(item)
            await self.session.flush()
            await self.inventory.reserve(order=order, item=item, reservation_minutes=automation.reservation_minutes)

        order.subtotal_amount = subtotal
        order.total_amount = subtotal
        order.cost_amount = cost
        self.audit.log(actor_user_id=user_id, action="order.create", resource_type="order", resource_id=order.id, metadata={"order_number": order.order_number})
        self.outbox.add(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.created",
            payload={"order_id": str(order.id), "user_id": str(user_id), "order_number": order.order_number},
        )
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def list_orders(self, *, user_id: UUID, limit: int = 50, offset: int = 0) -> list[Order]:
        result = await self.session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().unique().all())

    async def get_order(self, *, user_id: UUID, order_id: UUID) -> Order:
        result = await self.session.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
        order = result.scalar_one_or_none()
        if order is None:
            raise AppError("orders.not_found", status.HTTP_404_NOT_FOUND)
        return order

    def _order_number(self) -> str:
        return f"RS-{secrets.token_hex(10).upper()}"
