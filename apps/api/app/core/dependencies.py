from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_access_token, hash_secret
from app.models import ApiKey, RefreshToken, Role, User

bearer = HTTPBearer(auto_error=False)


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def current_user(
    session: AsyncSession = Depends(db_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> User:
    if credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = UUID(payload["sub"])
        except Exception as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.invalid_token") from exc
        user = await session.get(User, user_id)
        if user is None or user.status != "active":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.inactive_user")
        session_id = payload.get("sid")
        if session_id:
            active_session = await session.scalar(
                select(RefreshToken.id).where(
                    RefreshToken.user_id == user.id,
                    RefreshToken.session_id == UUID(session_id),
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > datetime.now(UTC),
                )
            )
            if active_session is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.session_revoked")
        return user

    if x_api_key:
        key_hash = hash_secret(x_api_key)
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.revoked_at.is_(None),
                (ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > datetime.now(UTC)),
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.invalid_api_key")
        user = await session.get(User, api_key.owner_user_id)
        if user is None or user.status != "active":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.inactive_user")
        api_key.last_used_at = datetime.now(UTC)
        await session.commit()
        return user

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.required")


def require_roles(*role_names: str):
    async def guard(
        user: User = Depends(current_user),
        session: AsyncSession = Depends(db_session),
    ) -> User:
        role = await session.get(Role, user.role_id)
        if role is None or role.name not in role_names:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="auth.forbidden")
        return user

    return guard


async def telegram_service(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    configured = settings.telegram_service_api_key
    if configured is None or x_api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.service_key_required")
    if not secrets.compare_digest(x_api_key, configured.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="auth.invalid_service_key")


def require_telegram_service_or_roles(*role_names: str):
    async def guard(
        session: AsyncSession = Depends(db_session),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> User | None:
        configured = settings.telegram_service_api_key
        if configured and x_api_key and secrets.compare_digest(x_api_key, configured.get_secret_value()):
            return None
        user = await current_user(session=session, credentials=credentials, x_api_key=x_api_key)
        role = await session.get(Role, user.role_id)
        if role is None or role.name not in role_names:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="auth.forbidden")
        return user

    return guard
