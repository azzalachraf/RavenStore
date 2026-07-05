from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, JsonDict, TimestampedOut


class AnalyticsSummaryOut(APIModel):
    revenue: Decimal
    profit: Decimal
    orders: int
    visitors: int
    telegram_users: int
    website_users: int
    best_selling_products: list[JsonDict]
    top_categories: list[JsonDict]
    conversion_rate: Decimal
    payment_statistics: JsonDict


class SupportTicketCreate(APIModel):
    subject_key: str
    message: str = Field(min_length=1, max_length=5000)


class SupportTicketOut(TimestampedOut):
    user_id: UUID
    subject_key: str
    status: str
    priority: str
    assigned_to_user_id: UUID | None


class NotificationOut(TimestampedOut):
    user_id: UUID | None
    channel: str
    title_key: str
    body_key: str
    status: str
    payload: JsonDict


class LanguageOut(TimestampedOut):
    code: str
    name: str
    is_rtl: bool
    is_active: bool


class ReferralOut(TimestampedOut):
    referrer_user_id: UUID
    referred_user_id: UUID | None
    code: str
    reward_amount: Decimal
    status: str


class SettingOut(TimestampedOut):
    key: str
    value: JsonDict
    is_secret: bool


class SettingUpsert(APIModel):
    value: JsonDict
    is_secret: bool = False


class TranslationUpsert(APIModel):
    value: str = Field(min_length=1, max_length=10000)


class LanguageUpsert(APIModel):
    name: str = Field(min_length=2, max_length=80)
    is_rtl: bool = False
    is_active: bool = True


class SupportReplyIn(APIModel):
    message: str = Field(min_length=1, max_length=5000)


class ReferralRewardIn(APIModel):
    amount: Decimal = Field(gt=0)
