from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session
from app.core.crypto import cipher
from app.models import DeliveryQueue, Order, User
from app.schemas.orders import OrderCreate, OrderOut
from app.services.orders import OrderService

router = APIRouter()


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    return await OrderService(session).create_order(user_id=user.id, payload=payload)


@router.get("", response_model=list[OrderOut])
async def list_orders(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    return await OrderService(session).list_orders(user_id=user.id, limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    return await OrderService(session).get_order(user_id=user.id, order_id=order_id)


@router.get("/{order_id}/deliveries")
async def order_deliveries(
    order_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    owned = await session.scalar(select(Order.id).where(Order.id == order_id, Order.user_id == user.id))
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="orders.not_found")
    deliveries = list(
        (
            await session.scalars(
                select(DeliveryQueue).where(DeliveryQueue.order_id == order_id).order_by(DeliveryQueue.created_at)
            )
        ).all()
    )
    return [
        {
            "id": str(delivery.id),
            "order_item_id": str(delivery.order_item_id),
            "delivery_type": delivery.delivery_type,
            "status": delivery.status,
            "delivery": cipher.decrypt(delivery.payload_encrypted)
            if delivery.status == "completed" and delivery.payload_encrypted
            else None,
            "completed_at": delivery.completed_at,
        }
        for delivery in deliveries
    ]
