from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def log(self, *, actor_user_id: UUID | None, action: str, resource_type: str, resource_id: UUID | None, metadata: dict) -> None:
        self.session.add(
            ActivityLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                activity_metadata=metadata,
            )
        )

