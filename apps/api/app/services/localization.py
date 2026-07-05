from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Language, TranslationKey
from app.services.audit import AuditService
from app.services.outbox import OutboxService


class LocalizationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditService(session)
        self.outbox = OutboxService(session)

    async def upsert_translation(self, *, language_code: str, key: str, value: str, actor_id: UUID) -> TranslationKey:
        language = await self.session.scalar(select(Language).where(Language.code == language_code, Language.is_active.is_(True)))
        if language is None:
            raise AppError("languages.not_found", status.HTTP_404_NOT_FOUND)
        translation = await self.session.scalar(
            select(TranslationKey)
            .where(TranslationKey.language_code == language_code, TranslationKey.key == key)
            .with_for_update()
        )
        if translation is None:
            translation = TranslationKey(language_code=language_code, key=key, value=value)
            self.session.add(translation)
            await self.session.flush()
        else:
            translation.value = value
        self.audit.log(
            actor_user_id=actor_id,
            action="translation.upsert",
            resource_type="translation",
            resource_id=translation.id,
            metadata={"language_code": language_code, "key": key},
        )
        self.outbox.add(
            aggregate_type="translation",
            aggregate_id=translation.id,
            event_type="translation.updated",
            payload={"translation_id": str(translation.id), "language_code": language_code, "key": key},
            cache_tags=[f"translations:{language_code}"],
        )
        await self.session.commit()
        return translation

    async def upsert_language(
        self,
        *,
        code: str,
        name: str,
        is_rtl: bool,
        is_active: bool,
        actor_id: UUID,
    ) -> Language:
        language = await self.session.scalar(select(Language).where(Language.code == code).with_for_update())
        if language is None:
            language = Language(code=code, name=name, is_rtl=is_rtl, is_active=is_active)
            self.session.add(language)
            await self.session.flush()
        else:
            language.name = name
            language.is_rtl = is_rtl
            language.is_active = is_active
        self.audit.log(
            actor_user_id=actor_id,
            action="language.upsert",
            resource_type="language",
            resource_id=language.id,
            metadata={"code": code},
        )
        self.outbox.add(
            aggregate_type="language",
            aggregate_id=language.id,
            event_type="language.updated",
            payload={"language_id": str(language.id), "language_code": code},
            cache_tags=[f"translations:{code}"],
        )
        await self.session.commit()
        return language
