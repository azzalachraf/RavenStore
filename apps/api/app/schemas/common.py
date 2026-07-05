from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedOut(APIModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class Money(APIModel):
    amount: Decimal = Field(decimal_places=2)
    currency: str = Field(min_length=3, max_length=12)


JsonDict = dict[str, Any]

