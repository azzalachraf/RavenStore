from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session, require_roles
from app.models import User
from app.schemas.misc import SupportReplyIn, SupportTicketCreate, SupportTicketOut
from app.services.support import SupportService

router = APIRouter()


@router.post("/tickets", response_model=SupportTicketOut, status_code=201)
async def create_ticket(
    payload: SupportTicketCreate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    return await SupportService(session).create_ticket(user_id=user.id, subject_key=payload.subject_key, message=payload.message)


@router.get("/tickets", response_model=list[SupportTicketOut])
async def list_tickets(
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    return await SupportService(session).tickets(user_id=user.id)


@router.get("/tickets/{ticket_id}/messages")
async def ticket_messages(
    ticket_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    return await SupportService(session).messages(ticket_id=ticket_id, actor_id=user.id, is_admin=False)


@router.post("/tickets/{ticket_id}/reply", status_code=201)
async def customer_reply(
    ticket_id: UUID,
    payload: SupportReplyIn,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    reply = await SupportService(session).reply(
        ticket_id=ticket_id,
        actor_id=user.id,
        message=payload.message,
        is_admin=False,
    )
    return {"id": str(reply.id), "message_key": "support.reply_created"}


@router.post("/admin/tickets/{ticket_id}/reply", status_code=201)
async def admin_reply(
    ticket_id: UUID,
    payload: SupportReplyIn,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin", "Support")),
):
    reply = await SupportService(session).reply(
        ticket_id=ticket_id,
        actor_id=admin.id,
        message=payload.message,
        is_admin=True,
    )
    return {"id": str(reply.id), "message_key": "support.reply_created"}
