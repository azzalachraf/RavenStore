from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class TelegramIdentityIn(APIModel):
    telegram_id: int = Field(gt=0)
    username: str | None = Field(default=None, max_length=128)
    first_name: str | None = Field(default=None, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    language_code: str | None = Field(default=None, max_length=16)
    referral_code: str | None = Field(default=None, max_length=64)


class TelegramLanguageIn(TelegramIdentityIn):
    locale: str = Field(pattern="^(en|ar)$")


class TelegramSettingsIn(APIModel):
    notifications_enabled: bool


class TelegramSessionOut(APIModel):
    access_token: str
    locale: str
    user_id: UUID
    referral_code: str | None = None
    notifications_enabled: bool


class TelegramProfileOut(APIModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    locale: str
    language_code: str | None
    country: str | None
    notifications_enabled: bool
