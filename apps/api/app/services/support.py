from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.errors import AppError
from app.models import SupportMessage, SupportTicket
from app.services.outbox import OutboxService


class SupportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.outbox = OutboxService(session)

    async def create_ticket(self, *, user_id: UUID, subject_key: str, message: str) -> SupportTicket:
        ticket = SupportTicket(user_id=user_id, subject_key=subject_key, status="open", priority="normal")
        self.session.add(ticket)
        await self.session.flush()
        self.session.add(SupportMessage(ticket_id=ticket.id, sender_user_id=user_id, body_encrypted=cipher.encrypt(message)))
        self.outbox.add(
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            event_type="support.ticket_created",
            payload={"ticket_id": str(ticket.id), "user_id": str(user_id)},
            audience="admin",
        )
        await self.session.commit()
        return ticket

    async def tickets(self, *, user_id: UUID | None = None) -> list[SupportTicket]:
        statement = select(SupportTicket).order_by(SupportTicket.created_at.desc())
        if user_id:
            statement = statement.where(SupportTicket.user_id == user_id)
        return list((await self.session.scalars(statement)).all())

    async def messages(self, *, ticket_id: UUID, actor_id: UUID, is_admin: bool) -> list[dict]:
        ticket = await self._ticket(ticket_id)
        if not is_admin and ticket.user_id != actor_id:
            raise AppError("support.ticket_not_found", status.HTTP_404_NOT_FOUND)
        rows = await self.session.scalars(
            select(SupportMessage).where(SupportMessage.ticket_id == ticket_id).order_by(SupportMessage.created_at)
        )
        return [
            {
                "id": str(message.id),
                "sender_user_id": str(message.sender_user_id) if message.sender_user_id else None,
                "message": cipher.decrypt(message.body_encrypted),
                "created_at": message.created_at,
            }
            for message in rows.all()
        ]

    async def reply(self, *, ticket_id: UUID, actor_id: UUID, message: str, is_admin: bool) -> SupportMessage:
        ticket = await self._ticket(ticket_id)
        if not is_admin and ticket.user_id != actor_id:
            raise AppError("support.ticket_not_found", status.HTTP_404_NOT_FOUND)
        reply = SupportMessage(
            ticket_id=ticket.id,
            sender_user_id=actor_id,
            body_encrypted=cipher.encrypt(message),
        )
        self.session.add(reply)
        await self.session.flush()
        event_type = "support.reply_added" if is_admin else "support.customer_replied"
        self.outbox.add(
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            event_type=event_type,
            payload={"ticket_id": str(ticket.id), "user_id": str(ticket.user_id)},
            audience="customer" if is_admin else "admin",
        )
        await self.session.commit()
        return reply

    async def _ticket(self, ticket_id: UUID) -> SupportTicket:
        ticket = await self.session.get(SupportTicket, ticket_id, with_for_update=True)
        if ticket is None:
            raise AppError("support.ticket_not_found", status.HTTP_404_NOT_FOUND)
        return ticket
