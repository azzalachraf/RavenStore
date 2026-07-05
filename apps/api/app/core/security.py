from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from uuid import uuid4

from jose import JWTError, jwt
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("$argon2"):
        try:
            return password_hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    if password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        encoded = password.encode()
        if len(encoded) > 72:
            return False
        try:
            return bcrypt.checkpw(encoded, password_hash.encode())
        except ValueError:
            return False
    return False


def password_needs_rehash(password_hash: str) -> bool:
    if not password_hash.startswith("$argon2"):
        return True
    try:
        return password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def hash_secret(value: str, *, pepper: str | None = None) -> str:
    secret = pepper or settings.api_key_pepper
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_access_token(
    subject: UUID,
    role: str,
    extra: dict[str, Any] | None = None,
    *,
    session_id: UUID | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "jti": str(uuid4()),
        "sid": str(session_id) if session_id else None,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: UUID, *, session_id: UUID) -> tuple[str, datetime, str]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    token_id = secrets.token_urlsafe(32)
    payload = {
        "sub": str(subject),
        "jti": token_id,
        "sid": str(session_id),
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_refresh_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at, token_id


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise ValueError("auth.invalid_token") from exc
    if payload.get("type") != "access":
        raise ValueError("auth.invalid_token_type")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_refresh_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise ValueError("auth.invalid_token") from exc
    if payload.get("type") != "refresh":
        raise ValueError("auth.invalid_token_type")
    return payload


def generate_public_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"
