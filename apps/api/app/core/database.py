from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

import os
import sys
from sqlalchemy.pool import NullPool

extra_args = {}
if os.getenv("RUN_INTEGRATION_TESTS") == "1" or "pytest" in sys.modules:
    extra_args["poolclass"] = NullPool
else:
    extra_args["pool_size"] = settings.database_pool_size
    extra_args["max_overflow"] = settings.database_max_overflow
    extra_args["pool_timeout"] = settings.database_pool_timeout_seconds
    extra_args["pool_recycle"] = settings.database_pool_recycle_seconds

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    **extra_args
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
