from __future__ import annotations

import asyncio
import json
import socket
import time
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import httpx

from raven_bot.config import settings
from raven_bot.domain import (
    BotSession,
    Category,
    Order,
    PaymentCreated,
    Product,
    ReferralStats,
    SupportTicket,
    TelegramIdentity,
    WalletSummary,
)
from raven_bot.logging import logger


class APIError(Exception):
    def __init__(self, message_key: str, status_code: int | None = None):
        self.message_key = message_key
        self.status_code = status_code
        super().__init__(message_key)


class RavenAPI:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url.rstrip("/"),
            timeout=settings.api_timeout_seconds,
            headers={"User-Agent": "RavenStoreTelegramBot/0.1"},
        )
        self._translation_cache: dict[str, tuple[float, dict[str, str]]] = {}
        self._closed = asyncio.Event()

    async def close(self) -> None:
        self._closed.set()
        await self._client.aclose()

    async def healthy(self) -> bool:
        try:
            response = await self._client.get("/categories", timeout=3)
            return response.is_success
        except httpx.HTTPError:
            return False

    async def watch_events(self) -> None:
        """Consumes invalidations only; all business data is fetched from REST on demand."""
        retry_seconds = 1
        last_event_id: str | None = None
        last_checkpoint_at = 0.0
        consumer_name = f"telegram-bot:{socket.gethostname()}"
        while not self._closed.is_set():
            headers = {"Accept": "text/event-stream"}
            if settings.api_service_key_value:
                headers["X-API-Key"] = settings.api_service_key_value
            if last_event_id:
                headers["Last-Event-ID"] = last_event_id
            try:
                async with self._client.stream(
                    "GET",
                    "/events/stream",
                    params={"topics": "catalog,inventory,localization,settings"},
                    headers=headers,
                    timeout=None,
                ) as response:
                    response.raise_for_status()
                    retry_seconds = 1
                    data = ""
                    async for line in response.aiter_lines():
                        if line.startswith("id:"):
                            last_event_id = line[3:].strip()
                        elif line.startswith("data:"):
                            data += line[5:].strip()
                        elif not line and data:
                            event = json.loads(data)
                            self._apply_invalidation(event)
                            data = ""
                        if not line and time.monotonic() - last_checkpoint_at >= 30:
                            await self._checkpoint(consumer_name, last_event_id)
                            last_checkpoint_at = time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("events.stream_disconnected", error=str(exc), retry_seconds=retry_seconds)
                try:
                    await asyncio.wait_for(self._closed.wait(), timeout=retry_seconds)
                except TimeoutError:
                    pass
                retry_seconds = min(30, retry_seconds * 2)

    def _apply_invalidation(self, event: dict[str, Any]) -> None:
        tags = {str(tag) for tag in event.get("cache_tags", [])}
        if "translations" in tags:
            language_code = event.get("payload", {}).get("language_code")
            if language_code:
                self._translation_cache.pop(str(language_code), None)
            else:
                self._translation_cache.clear()
        logger.info(
            "events.invalidation_received",
            event_id=event.get("event_id"),
            event_type=event.get("event_type"),
            cache_tags=sorted(tags),
        )

    async def _checkpoint(self, consumer_name: str, last_event_id: str | None) -> None:
        if not settings.api_service_key_value:
            return
        try:
            await self._request(
                "PUT",
                f"/events/consumers/{consumer_name}/checkpoint",
                json={"last_stream_id": last_event_id, "status": "healthy", "metadata": {"client": "telegram"}},
            )
        except APIError as exc:
            logger.warning("events.checkpoint_failed", message_key=exc.message_key)

    async def bootstrap_session(self, identity: TelegramIdentity) -> BotSession:
        try:
            data = await self._request("POST", "/telegram/session", json=identity.model_dump())
            return BotSession.model_validate(data)
        except APIError as exc:
            if exc.status_code == 404:
                logger.warning("telegram.session_endpoint_missing")
                return BotSession(locale=identity.language_code or settings.default_locale)
            raise

    async def save_language(self, token: str | None, locale: str, identity: TelegramIdentity) -> BotSession:
        payload = {"locale": locale, **identity.model_dump()}
        try:
            data = await self._request("PATCH", "/telegram/users/me/language", json=payload, token=token)
            return BotSession.model_validate(data)
        except APIError as exc:
            if exc.status_code == 404:
                return BotSession(access_token=token, locale=locale)
            raise

    async def get_api_key(self, token: str | None) -> dict[str, Any]:
        self._require_token(token)
        try:
            return await self._request("GET", "/telegram/users/me/api-key", token=token)
        except APIError as exc:
            if exc.status_code == 404:
                return {}
            raise

    async def generate_api_key(self, token: str | None) -> dict[str, Any]:
        self._require_token(token)
        return await self._request("POST", "/telegram/users/me/api-key", token=token)

    async def translations(self, locale: str) -> dict[str, str]:
        cached = self._translation_cache.get(locale)
        if cached and time.time() - cached[0] < 60:
            return cached[1]
        try:
            data = await self._request("GET", f"/languages/{locale}/translations")
            catalog = {str(key): str(value) for key, value in data.items()}
            self._translation_cache[locale] = (time.time(), catalog)
            return catalog
        except APIError:
            return {}

    async def categories(self) -> list[Category]:
        data = await self._request("GET", "/categories")
        return [Category.model_validate(item) for item in data]

    async def products(
        self,
        *,
        page: int,
        page_size: int,
        category_id: UUID | None = None,
        query: str | None = None,
        filter_name: str | None = None,
    ) -> list[Product]:
        params: dict[str, Any] = {"limit": page_size, "offset": max(page - 1, 0) * page_size}
        if category_id:
            params["category_id"] = str(category_id)
        if query:
            params["search"] = query
        if filter_name:
            params["filter"] = filter_name
        data = await self._request("GET", "/products", params=params)
        return [Product.model_validate(item) for item in data]

    async def product(self, slug: str) -> Product:
        data = await self._request("GET", f"/products/{slug}")
        return Product.model_validate(data)

    async def create_order(self, token: str | None, variant_id: UUID, quantity: int = 1) -> Order:
        self._require_token(token)
        data = await self._request(
            "POST",
            "/orders",
            json={"items": [{"product_variant_id": str(variant_id), "quantity": quantity}]},
            token=token,
            idempotent=True,
        )
        return Order.model_validate(data)

    async def orders(self, token: str | None, status: str | None = None) -> list[Order]:
        self._require_token(token)
        params = {"status": status} if status else None
        data = await self._request("GET", "/orders", params=params, token=token)
        return [Order.model_validate(item) for item in data]

    async def request_payment(self, token: str | None, order_id: UUID, method: str) -> PaymentCreated:
        self._require_token(token)
        data = await self._request(
            "POST",
            "/payments/request",
            json={"order_id": str(order_id), "method": method},
            token=token,
            idempotent=True,
        )
        return PaymentCreated.model_validate(data)

    async def submit_payment_verification(self, payment_token: str, payment_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/payments/verify",
            json={"payment_token": payment_token, "tx_hash": payment_id},
            idempotent=True,
        )

    async def referral_stats(self, token: str | None, bot_username: str) -> ReferralStats:
        self._require_token(token)
        try:
            data = await self._request("GET", "/referral/stats", token=token)
            return ReferralStats.model_validate(data)
        except APIError as exc:
            if exc.status_code != 404:
                raise
        rows = await self._request("GET", "/referral", token=token)
        code = rows[0].get("code") if rows else None
        return ReferralStats(
            code=code,
            link=f"https://t.me/{bot_username}?start={code}" if code else None,
            invited_count=len(rows),
            reward_amount=sum((item.get("reward_amount", 0) for item in rows), start=0),
        )

    async def wallet(self, token: str | None) -> WalletSummary:
        self._require_token(token)
        try:
            data = await self._request("GET", "/wallet/summary", token=token)
            return WalletSummary.model_validate(data)
        except APIError as exc:
            if exc.status_code != 404:
                raise
        orders = await self.orders(token)
        return WalletSummary(purchase_count=len(orders))

    async def support_tickets(self, token: str | None) -> list[SupportTicket]:
        self._require_token(token)
        try:
            data = await self._request("GET", "/support/tickets", token=token)
        except APIError as exc:
            if exc.status_code == 404:
                return []
            raise
        return [SupportTicket.model_validate(item) for item in data]

    async def create_support_ticket(self, token: str | None, subject_key: str, message: str) -> SupportTicket:
        self._require_token(token)
        data = await self._request(
            "POST",
            "/support/tickets",
            json={"subject_key": subject_key, "message": message},
            token=token,
            idempotent=True,
        )
        return SupportTicket.model_validate(data)

    async def profile(self, token: str | None) -> dict[str, Any]:
        self._require_token(token)
        try:
            return await self._request("GET", "/telegram/users/me", token=token)
        except APIError as exc:
            if exc.status_code == 404:
                return {}
            raise

    async def analytics_event(
        self,
        token: str | None,
        event_type: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            await self._request(
                "POST",
                "/analytics/events",
                json={"event_type": event_type, "source": "telegram", "metadata": dict(metadata or {})},
                token=token,
            )
        except APIError:
            logger.warning("analytics.event_dropped", event_type=event_type)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: Mapping[str, Any] | None = None,
        token: str | None = None,
        idempotent: bool = False,
    ) -> Any:
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif settings.api_service_key_value:
            headers["X-API-Key"] = settings.api_service_key_value
        if idempotent:
            headers["Idempotency-Key"] = self._idempotency_key(method, path, json)

        last_error: Exception | None = None
        for attempt in range(settings.api_retries + 1):
            try:
                response = await self._client.request(method, path, json=json, params=params, headers=headers)
                if response.status_code == 429:
                    raise APIError("error.rate_limited", 429)
                if response.status_code in {401, 403}:
                    raise APIError("error.auth_required", response.status_code)
                if response.status_code >= 400:
                    raise APIError(self._message_key(response), response.status_code)
                if response.content:
                    return response.json()
                return {}
            except httpx.TimeoutException as exc:
                last_error = exc
                await asyncio.sleep(0.2 * (attempt + 1))
            except httpx.TransportError as exc:
                last_error = exc
                await asyncio.sleep(0.2 * (attempt + 1))
        if isinstance(last_error, httpx.TimeoutException):
            raise APIError("error.timeout") from last_error
        raise APIError("error.api_unavailable") from last_error

    def _message_key(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
            return payload.get("error", {}).get("message_key") or payload.get("detail") or "error.unexpected"
        except Exception:
            return "error.unexpected"

    def _idempotency_key(self, method: str, path: str, body: Any | None) -> str:
        body_hash = str(abs(hash(str(body))))[:16]
        return f"tg:{method}:{path}:{body_hash}:{time.time_ns()}"

    def _require_token(self, token: str | None) -> None:
        if not token and not settings.api_service_key_value:
            raise APIError("error.auth_required", 401)
