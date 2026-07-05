from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import current_user
from app.models import User
from app.schemas.users import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user

