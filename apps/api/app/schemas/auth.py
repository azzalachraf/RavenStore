from __future__ import annotations

from pydantic import EmailStr, Field, field_validator
from datetime import datetime
from uuid import UUID

from app.schemas.common import APIModel


class RegisterIn(APIModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str | None = Field(default=None, max_length=160)
    locale: str = Field(default="en", pattern="^(en|ar)$")

    @field_validator("password")
    @classmethod
    def reject_common_passwords(cls, value: str) -> str:
        if value.casefold() in {"password1234", "123456789012", "qwerty123456", "ravenstore123"}:
            raise ValueError("auth.password_too_common")
        return value


class LoginIn(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(APIModel):
    refresh_token: str = Field(min_length=32, max_length=4096)


class SessionOut(APIModel):
    session_id: UUID
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    user_agent: str | None


class TokenPairOut(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
