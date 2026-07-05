from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session, require_roles
from app.models import Referral, User
from app.schemas.misc import ReferralOut, ReferralRewardIn
from app.services.outbox import OutboxService

router = APIRouter()


@router.get("/stats")
async def referral_stats(session: AsyncSession = Depends(db_session), user: User = Depends(current_user)):
    rows = list(
        (await session.scalars(select(Referral).where(Referral.referrer_user_id == user.id).order_by(Referral.created_at.desc()))).all()
    )
    reward = await session.scalar(
        select(func.coalesce(func.sum(Referral.reward_amount), 0)).where(Referral.referrer_user_id == user.id)
    )
    from app.core.config import settings

    link = f"https://t.me/{settings.telegram_bot_username}?start={user.referral_code}" if settings.telegram_bot_username else None
    return {
        "code": user.referral_code,
        "link": link,
        "invited_count": len(rows),
        "reward_amount": reward or 0,
        "invited_users": [
            {"user_id": str(row.referred_user_id), "status": row.status, "reward_amount": row.reward_amount}
            for row in rows
        ],
    }


@router.get("", response_model=list[ReferralOut])
async def my_referrals(session: AsyncSession = Depends(db_session), user: User = Depends(current_user)):
    result = await session.execute(select(Referral).where(Referral.referrer_user_id == user.id).order_by(Referral.created_at.desc()))
    return list(result.scalars().all())


@router.post("/{referral_id}/reward")
async def reward_referral(
    referral_id: UUID,
    payload: ReferralRewardIn,
    session: AsyncSession = Depends(db_session),
    _: User = Depends(require_roles("Owner", "Admin")),
):
    referral = await session.get(Referral, referral_id, with_for_update=True)
    if referral is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="referrals.not_found")
    if referral.status == "rewarded":
        return {"message_key": "referrals.already_rewarded"}
    referral.reward_amount = payload.amount
    referral.status = "rewarded"
    OutboxService(session).add(
        aggregate_type="referral",
        aggregate_id=referral.id,
        event_type="referral.rewarded",
        payload={
            "referral_id": str(referral.id),
            "user_id": str(referral.referrer_user_id),
            "amount": str(payload.amount),
        },
    )
    await session.commit()
    return {"message_key": "referrals.rewarded"}
