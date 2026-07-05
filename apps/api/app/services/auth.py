from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import structlog
from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_secret,
    password_needs_rehash,
    verify_password,
)
from app.infrastructure.redis_runtime import redis_runtime
from app.models import RefreshToken, Role, SecurityEvent, User

logger = structlog.get_logger("ravenstore.auth")
DUMMY_PASSWORD_HASH = hash_password("ravenstore-dummy-password-never-used")


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None,
        locale: str,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        role = await self._role("Customer")
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            password_changed_at=datetime.now(UTC),
            display_name=display_name,
            role_id=role.id,
            locale=locale,
        )
        self.session.add(user)
        await self.session.flush()
        self._security_event("auth.registered", "info", "success", user, ip_hash, user_agent)
        return await self._issue_tokens(user, role.name, ip_hash=ip_hash, user_agent=user_agent)

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        normalized_email = email.lower()
        await self._enforce_distributed_lockout(normalized_email, ip_hash)
        user = await self.session.scalar(select(User).where(User.email == normalized_email).with_for_update())
        valid = verify_password(password, user.password_hash) if user and user.password_hash else verify_password(password, DUMMY_PASSWORD_HASH)
        if user is None or not valid:
            await self._record_failed_login(user, normalized_email, ip_hash, user_agent)
            raise AppError("auth.invalid_credentials", status.HTTP_401_UNAUTHORIZED)
        now = datetime.now(UTC)
        if user.locked_until and user.locked_until > now:
            self._security_event("auth.login_blocked", "warning", "blocked", user, ip_hash, user_agent)
            await self.session.commit()
            raise AppError("auth.account_locked", status.HTTP_423_LOCKED)
        if user.status != "active":
            self._security_event("auth.login_blocked", "warning", "blocked", user, ip_hash, user_agent)
            await self.session.commit()
            raise AppError("auth.inactive_user", status.HTTP_401_UNAUTHORIZED)
        role = await self.session.get(Role, user.role_id)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        if user.password_hash and password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            user.password_changed_at = now
        await self._clear_distributed_failures(normalized_email, ip_hash)
        self._security_event("auth.login", "info", "success", user, ip_hash, user_agent)
        return await self._issue_tokens(user, role.name if role else "Customer", ip_hash=ip_hash, user_agent=user_agent)

    async def refresh(
        self,
        refresh_token: str,
        *,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("auth.invalid_token", status.HTTP_401_UNAUTHORIZED) from exc
        token_hash = hash_secret(refresh_token)
        record = await self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
        now = datetime.now(UTC)
        if record is None or record.user_id != user_id:
            raise AppError("auth.invalid_token", status.HTTP_401_UNAUTHORIZED)
        if record.revoked_at is not None:
            record.reused_at = now
            await self._revoke_user_sessions(user_id, now)
            self._security_event("auth.refresh_reuse", "critical", "blocked", None, ip_hash, user_agent, {"user_id": str(user_id)})
            await self.session.commit()
            raise AppError("auth.session_compromised", status.HTTP_401_UNAUTHORIZED)
        if record.expires_at <= now:
            record.revoked_at = now
            await self.session.commit()
            raise AppError("auth.refresh_expired", status.HTTP_401_UNAUTHORIZED)
        user = await self.session.get(User, user_id)
        if user is None or user.status != "active":
            raise AppError("auth.inactive_user", status.HTTP_401_UNAUTHORIZED)
        role = await self.session.get(Role, user.role_id)
        record.revoked_at = now
        record.last_used_at = now
        self._security_event("auth.refresh_rotated", "info", "success", user, ip_hash, user_agent)
        return await self._issue_tokens(
            user,
            role.name if role else "Customer",
            session_id=record.session_id,
            ip_hash=ip_hash,
            user_agent=user_agent,
        )

    async def logout(self, refresh_token: str) -> None:
        record = await self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_secret(refresh_token)).with_for_update()
        )
        if record and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            await self.session.commit()

    async def sessions(self, user_id: UUID) -> list[RefreshToken]:
        result = await self.session.scalars(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > datetime.now(UTC))
            .order_by(RefreshToken.created_at.desc())
        )
        return list(result.all())

    async def revoke_session(self, user_id: UUID, session_id: UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.session_id == session_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.commit()

    async def _issue_tokens(
        self,
        user: User,
        role_name: str,
        *,
        session_id: UUID | None = None,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        active_session_id = session_id or uuid4()
        access = create_access_token(user.id, role_name, session_id=active_session_id)
        refresh, expires_at, token_id = create_refresh_token(user.id, session_id=active_session_id)
        self.session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_secret(refresh),
                token_id=token_id,
                session_id=active_session_id,
                expires_at=expires_at,
                created_ip_hash=ip_hash,
                user_agent=(user_agent or "")[:512] or None,
            )
        )
        await self.session.commit()
        return access, refresh

    async def _record_failed_login(
        self,
        user: User | None,
        email: str,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> None:
        locked = False
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.login_max_attempts:
                user.locked_until = datetime.now(UTC) + timedelta(seconds=settings.account_lockout_seconds)
                locked = True
        distributed_count = await self._increment_distributed_failures(email, ip_hash)
        self._security_event(
            "auth.login_failed",
            "warning" if not locked else "high",
            "blocked" if locked else "failure",
            user,
            ip_hash,
            user_agent,
            {"distributed_attempts": distributed_count},
        )
        await self.session.commit()
        logger.warning("auth.login_failed", user_id=str(user.id) if user else None, ip_hash=ip_hash, locked=locked)

    async def _enforce_distributed_lockout(self, email: str, ip_hash: str | None) -> None:
        if not redis_runtime.client:
            return
        keys = self._failure_keys(email, ip_hash)
        values = await redis_runtime.client.mget(keys)
        if any(int(value or 0) >= settings.login_max_attempts for value in values):
            raise AppError("auth.too_many_attempts", status.HTTP_429_TOO_MANY_REQUESTS)

    async def _increment_distributed_failures(self, email: str, ip_hash: str | None) -> int:
        if not redis_runtime.client:
            return 0
        counts: list[int] = []
        for key in self._failure_keys(email, ip_hash):
            count = int(await redis_runtime.client.incr(key))
            if count == 1:
                await redis_runtime.client.expire(key, settings.login_attempt_window_seconds)
            counts.append(count)
        return max(counts, default=0)

    async def _clear_distributed_failures(self, email: str, ip_hash: str | None) -> None:
        if redis_runtime.client:
            await redis_runtime.client.delete(*self._failure_keys(email, ip_hash))

    def _failure_keys(self, email: str, ip_hash: str | None) -> list[str]:
        keys = [f"ravenstore:auth:fail:email:{hash_secret(email)}"]
        if ip_hash:
            keys.append(f"ravenstore:auth:fail:ip:{ip_hash}")
        return keys

    async def _revoke_user_sessions(self, user_id: UUID, now: datetime) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def _security_event(
        self,
        event_type: str,
        severity: str,
        outcome: str,
        user: User | None,
        ip_hash: str | None,
        user_agent: str | None,
        metadata: dict | None = None,
    ) -> None:
        self.session.add(
            SecurityEvent(
                actor_user_id=user.id if user else None,
                event_type=event_type,
                severity=severity,
                outcome=outcome,
                ip_hash=ip_hash,
                user_agent=(user_agent or "")[:512] or None,
                trace_id=structlog.contextvars.get_contextvars().get("request_id"),
                event_metadata=metadata or {},
            )
        )

    async def _role(self, name: str) -> Role:
        role = await self.session.scalar(select(Role).where(Role.name == name))
        if role:
            return role
        role = Role(name=name, description=f"{name} role", is_system=True)
        self.session.add(role)
        await self.session.flush()
        return role
