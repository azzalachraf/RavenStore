from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session
from app.models import Notification, User
from app.schemas.misc import NotificationOut

router = APIRouter()


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    result = await session.execute(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100))
    return list(result.scalars().all())

