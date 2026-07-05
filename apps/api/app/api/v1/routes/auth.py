from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session
from app.core.network import client_ip_hash
from app.models import User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, SessionOut, TokenPairOut
from app.services.auth import AuthService

router = APIRouter()


def _client_context(request: Request) -> tuple[str, str | None]:
    return client_ip_hash(request), request.headers.get("User-Agent")


@router.post("/register", response_model=TokenPairOut, status_code=201)
async def register(payload: RegisterIn, request: Request, session: AsyncSession = Depends(db_session)) -> TokenPairOut:
    ip_hash, user_agent = _client_context(request)
    access, refresh = await AuthService(session).register(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        locale=payload.locale,
        ip_hash=ip_hash,
        user_agent=user_agent,
    )
    return TokenPairOut(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenPairOut)
async def login(payload: LoginIn, request: Request, session: AsyncSession = Depends(db_session)) -> TokenPairOut:
    ip_hash, user_agent = _client_context(request)
    access, refresh = await AuthService(session).login(
        email=payload.email,
        password=payload.password,
        ip_hash=ip_hash,
        user_agent=user_agent,
    )
    return TokenPairOut(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPairOut)
async def refresh(payload: RefreshIn, request: Request, session: AsyncSession = Depends(db_session)) -> TokenPairOut:
    ip_hash, user_agent = _client_context(request)
    access, rotated = await AuthService(session).refresh(
        payload.refresh_token,
        ip_hash=ip_hash,
        user_agent=user_agent,
    )
    return TokenPairOut(access_token=access, refresh_token=rotated)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshIn, session: AsyncSession = Depends(db_session)) -> Response:
    await AuthService(session).logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions", response_model=list[SessionOut])
async def sessions(user: User = Depends(current_user), session: AsyncSession = Depends(db_session)) -> list[SessionOut]:
    records = await AuthService(session).sessions(user.id)
    grouped: dict[UUID, SessionOut] = {}
    for record in records:
        grouped.setdefault(
            record.session_id,
            SessionOut(
                session_id=record.session_id,
                created_at=record.created_at,
                expires_at=record.expires_at,
                last_used_at=record.last_used_at,
                user_agent=record.user_agent,
            ),
        )
    return list(grouped.values())


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> Response:
    await AuthService(session).revoke_session(user.id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
