from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_session, require_roles
from app.models import Language, TranslationKey, User
from app.schemas.misc import LanguageOut, LanguageUpsert, TranslationUpsert
from app.services.localization import LocalizationService

router = APIRouter()


@router.get("", response_model=list[LanguageOut])
async def list_languages(session: AsyncSession = Depends(db_session)):
    result = await session.execute(select(Language).where(Language.is_active.is_(True)).order_by(Language.code))
    return list(result.scalars().all())


@router.get("/{language_code}/translations")
async def translations(language_code: str, session: AsyncSession = Depends(db_session)) -> dict[str, str]:
    result = await session.execute(select(TranslationKey).where(TranslationKey.language_code == language_code))
    return {row.key: row.value for row in result.scalars().all()}


@router.put("/{language_code}", response_model=LanguageOut)
async def upsert_language(
    language_code: str,
    payload: LanguageUpsert,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    return await LocalizationService(session).upsert_language(
        code=language_code,
        name=payload.name,
        is_rtl=payload.is_rtl,
        is_active=payload.is_active,
        actor_id=admin.id,
    )


@router.put("/{language_code}/translations/{translation_key}")
async def upsert_translation(
    language_code: str,
    translation_key: str,
    payload: TranslationUpsert,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    translation = await LocalizationService(session).upsert_translation(
        language_code=language_code,
        key=translation_key,
        value=payload.value,
        actor_id=admin.id,
    )
    return {"id": str(translation.id), "key": translation.key, "language_code": translation.language_code}
