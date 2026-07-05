from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_session, require_roles
from app.models import Setting, User
from app.schemas.misc import SettingOut, SettingUpsert
from app.services.settings import SettingsService

router = APIRouter()


@router.get("", response_model=list[SettingOut])
async def list_settings(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin")),
):
    result = await session.scalars(select(Setting).order_by(Setting.key))
    return [
        {
            "id": setting.id,
            "key": setting.key,
            "value": {"configured": True} if setting.is_secret else setting.value,
            "is_secret": setting.is_secret,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at,
        }
        for setting in result.all()
    ]


@router.put("/{key}", response_model=SettingOut)
async def upsert_setting(
    key: str,
    payload: SettingUpsert,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    setting = await SettingsService(session).upsert(
        key=key,
        value=payload.value,
        is_secret=payload.is_secret,
        actor_id=admin.id,
    )
    if setting.is_secret:
        return {
            "id": setting.id,
            "key": setting.key,
            "value": {"configured": True},
            "is_secret": True,
            "created_at": setting.created_at,
            "updated_at": setting.updated_at,
        }
    return setting
