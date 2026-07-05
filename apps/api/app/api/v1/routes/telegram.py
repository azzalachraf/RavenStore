from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session, telegram_service
from app.core.security import create_access_token
from app.models import Referral, Role, TelegramUser, User
from app.schemas.telegram import (
    TelegramIdentityIn,
    TelegramLanguageIn,
    TelegramProfileOut,
    TelegramSessionOut,
    TelegramSettingsIn,
)

router = APIRouter()


@router.post("/session", response_model=TelegramSessionOut)
async def bootstrap_session(
    payload: TelegramIdentityIn,
    session: AsyncSession = Depends(db_session),
    _: None = Depends(telegram_service),
) -> TelegramSessionOut:
    telegram_user = await session.scalar(
        select(TelegramUser).where(TelegramUser.telegram_id == payload.telegram_id).with_for_update()
    )
    if telegram_user is None:
        role = await _customer_role(session)
        locale = _locale(payload.language_code)
        user = User(
            email=f"telegram-{payload.telegram_id}@users.ravenstore.internal",
            display_name=" ".join(value for value in [payload.first_name, payload.last_name] if value) or payload.username,
            role_id=role.id,
            locale=locale,
            status="active",
        )
        session.add(user)
        await session.flush()
        user.referral_code = f"rvn_{user.id.hex}"
        telegram_user = TelegramUser(user_id=user.id, telegram_id=payload.telegram_id)
        session.add(telegram_user)
    else:
        user = await session.get(User, telegram_user.user_id)
        if user is None or user.status != "active":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.inactive_user")
    telegram_user.username = payload.username
    telegram_user.first_name = payload.first_name
    telegram_user.last_name = payload.last_name
    telegram_user.language_code = payload.language_code
    telegram_user.last_seen_at = datetime.now(UTC)
    if payload.referral_code:
        await _attribute_referral(session, user, payload.referral_code)
    role = await session.get(Role, user.role_id)
    await session.commit()
    return TelegramSessionOut(
        access_token=create_access_token(user.id, role.name if role else "Customer"),
        locale=user.locale,
        user_id=user.id,
        referral_code=user.referral_code,
        notifications_enabled=telegram_user.notifications_enabled,
    )


@router.patch("/users/me/language", response_model=TelegramSessionOut)
async def set_language(
    payload: TelegramLanguageIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> TelegramSessionOut:
    telegram_user = await _telegram_user(session, user.id)
    user.locale = payload.locale
    telegram_user.language_code = payload.language_code
    telegram_user.last_seen_at = datetime.now(UTC)
    await session.commit()
    role = await session.get(Role, user.role_id)
    return TelegramSessionOut(
        access_token=create_access_token(user.id, role.name if role else "Customer"),
        locale=user.locale,
        user_id=user.id,
        referral_code=user.referral_code,
        notifications_enabled=telegram_user.notifications_enabled,
    )


@router.patch("/users/me/settings")
async def update_settings(
    payload: TelegramSettingsIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> dict[str, bool]:
    telegram_user = await _telegram_user(session, user.id)
    telegram_user.notifications_enabled = payload.notifications_enabled
    telegram_user.last_seen_at = datetime.now(UTC)
    await session.commit()
    return {"notifications_enabled": telegram_user.notifications_enabled}


@router.get("/users/me", response_model=TelegramProfileOut)
async def profile(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> TelegramProfileOut:
    telegram_user = await _telegram_user(session, user.id)
    return TelegramProfileOut(
        telegram_id=telegram_user.telegram_id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        locale=user.locale,
        language_code=telegram_user.language_code,
        country=telegram_user.country_code,
        notifications_enabled=telegram_user.notifications_enabled,
    )


async def _telegram_user(session: AsyncSession, user_id) -> TelegramUser:
    telegram_user = await session.scalar(select(TelegramUser).where(TelegramUser.user_id == user_id))
    if telegram_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="telegram.user_not_found")
    return telegram_user


async def _customer_role(session: AsyncSession) -> Role:
    role = await session.scalar(select(Role).where(Role.name == "Customer"))
    if role is None:
        role = Role(name="Customer", description="Customer role", is_system=True)
        session.add(role)
        await session.flush()
    return role


def _locale(language_code: str | None) -> str:
    return "ar" if (language_code or "").lower().startswith("ar") else "en"


async def _attribute_referral(session: AsyncSession, user: User, code: str) -> None:
    if code == user.referral_code:
        return
    existing = await session.scalar(select(Referral.id).where(Referral.referred_user_id == user.id))
    if existing:
        return
    referrer = await session.scalar(select(User).where(User.referral_code == code))
    if referrer is None or referrer.id == user.id:
        return
    session.add(
        Referral(
            referrer_user_id=referrer.id,
            referred_user_id=user.id,
            code=f"{code}-{user.id.hex[:12]}",
            status="pending",
        )
    )


@router.get("/users/me/api-key")
async def get_reseller_api_key(
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    from app.models import ApiKey
    key = await session.scalar(
        select(ApiKey).where(ApiKey.owner_user_id == user.id, ApiKey.revoked_at.is_(None))
    )
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="api_keys.not_found")
    return {
        "name": key.name,
        "created_at": key.created_at,
        "last_used_at": key.last_used_at,
    }


@router.post("/users/me/api-key")
async def generate_reseller_api_key(
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    from app.models import ApiKey
    from app.core.security import hash_secret
    import secrets
    existing_keys = list(
        (await session.scalars(
            select(ApiKey).where(ApiKey.owner_user_id == user.id, ApiKey.revoked_at.is_(None))
        )).all()
    )
    for k in existing_keys:
        k.revoked_at = datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    raw_key = f"rk_{token}"
    hashed = hash_secret(raw_key)
    prefix = f"{raw_key[:10]}..."
    new_key = ApiKey(
        owner_user_id=user.id,
        name=prefix,
        key_hash=hashed,
        scopes=["reseller"],
    )
    session.add(new_key)
    await session.flush()
    await session.commit()
    return {
        "api_key": raw_key,
        "name": prefix,
        "created_at": new_key.created_at,
    }
