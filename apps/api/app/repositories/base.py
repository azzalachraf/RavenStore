from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def get(self, object_id: UUID) -> ModelT | None:
        return await self.session.get(self.model, object_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[ModelT]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def one_or_none(self, statement: Select[tuple[ModelT]]) -> ModelT | None:
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def many(self, statement: Select[tuple[ModelT]]) -> list[ModelT]:
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

