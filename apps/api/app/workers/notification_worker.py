from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.i18n import translate
from app.core.resilience import call_with_resilience
from app.models import Notification, TelegramUser, User


class NotificationWorker:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_next(self) -> bool:
        result = await self.session.execute(
            select(Notification)
            .where(
                Notification.status == "queued",
                Notification.channel == "telegram",
                (Notification.next_attempt_at.is_(None)) | (Notification.next_attempt_at <= datetime.now(UTC)),
            )
            .order_by(Notification.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            return False
        if not settings.telegram_bot_token:
            notification.status = "dead_letter"
            notification.last_error = "notifications.telegram_not_configured"
            await self.session.commit()
            return True
        user = await self.session.get(User, notification.user_id) if notification.user_id else None
        result = await self.session.execute(select(TelegramUser).where(TelegramUser.user_id == notification.user_id))
        telegram_user = result.scalar_one_or_none()
        admin_fallback = bool(user and user.role.name in {"Owner", "Admin"} and settings.telegram_admin_id)
        if telegram_user is None and not admin_fallback:
            notification.status = "dead_letter"
            notification.last_error = "notifications.telegram_user_not_found"
            await self.session.commit()
            return True
        locale = user.locale if user else telegram_user.language_code if telegram_user else "en"
        chat_id = telegram_user.telegram_id if telegram_user else settings.telegram_admin_id
        text = f"{translate(notification.title_key, locale)}\n\n{translate(notification.body_key, locale)}"

        if notification.title_key == "notifications.delivery_completed.title":
            order_id = notification.payload.get("order_id")
            if order_id:
                from app.models import DeliveryQueue
                from app.core.crypto import cipher
                from uuid import UUID
                deliveries = await self.session.scalars(
                    select(DeliveryQueue).where(DeliveryQueue.order_id == UUID(str(order_id)), DeliveryQueue.status == "completed")
                )
                payloads = []
                for d in deliveries.all():
                    if d.payload_encrypted:
                        try:
                            decrypted = cipher.decrypt(d.payload_encrypted)
                            payloads.append(f"<code>{decrypted}</code>")
                        except Exception:
                            pass
                if payloads:
                    text += "\n\n🔑 <b>Your Delivery (tap to copy):</b>\n" + "\n".join(payloads)

        async def send() -> httpx.Response:
            async with httpx.AsyncClient(timeout=settings.external_http_timeout_seconds) as client:
                return await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                )

        try:
            response = await call_with_resilience(
                "telegram-notifications",
                send,
                retryable=lambda exc: isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)),
            )
        except Exception as exc:
            notification.attempt_count += 1
            notification.last_error = type(exc).__name__
            notification.status = "dead_letter" if notification.attempt_count >= 8 else "queued"
            notification.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=min(1800, 2**notification.attempt_count * 15)
            )
            await self.session.commit()
            return True
        if response.is_success:
            notification.status = "sent"
            notification.sent_at = datetime.now(UTC)
            notification.last_error = None
        else:
            notification.attempt_count += 1
            notification.last_error = response.text[:2000]
            if notification.attempt_count >= 8:
                notification.status = "dead_letter"
            else:
                notification.status = "queued"
                notification.next_attempt_at = datetime.now(UTC) + timedelta(
                    seconds=min(1800, 2**notification.attempt_count * 15)
                )
        await self.session.commit()
        return True
