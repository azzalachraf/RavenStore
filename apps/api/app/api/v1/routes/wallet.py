from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session
from app.models import Order, User

router = APIRouter()


@router.get("/summary")
async def wallet_summary(
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    purchase_count = await session.scalar(select(func.count(Order.id)).where(Order.user_id == user.id))
    return {"purchase_count": purchase_count or 0, "future_balance": 0, "currency": "USD"}
