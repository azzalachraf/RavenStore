from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.models import Setting
from app.services.audit import AuditService
from app.services.outbox import OutboxService


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditService(session)
        self.outbox = OutboxService(session)

    async def upsert(self, *, key: str, value: dict, is_secret: bool, actor_id: UUID) -> Setting:
        setting = await self.session.scalar(select(Setting).where(Setting.key == key).with_for_update())
        stored_value = (
            {"ciphertext": cipher.encrypt(json.dumps(value, separators=(",", ":"), ensure_ascii=True))}
            if is_secret
            else value
        )
        if setting is None:
            setting = Setting(key=key, value=stored_value, is_secret=is_secret)
            self.session.add(setting)
            await self.session.flush()
        else:
            setting.value = stored_value
            setting.is_secret = is_secret
        self.audit.log(
            actor_user_id=actor_id,
            action="setting.upsert",
            resource_type="setting",
            resource_id=setting.id,
            metadata={"key": key, "is_secret": is_secret},
        )
        self.outbox.add(
            aggregate_type="setting",
            aggregate_id=setting.id,
            event_type="settings.updated",
            payload={"setting_id": str(setting.id), "key": key},
            cache_tags=[f"settings:{key}"],
        )
        await self.session.commit()
        await self.session.refresh(setting)
        return setting
