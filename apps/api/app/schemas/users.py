from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr

from app.schemas.common import APIModel


class UserOut(APIModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    role_id: UUID
    status: str
    locale: str
    last_login_at: datetime | None

