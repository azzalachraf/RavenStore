from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.dependencies import db_session
from app.core.security import hash_secret
from app.integrations.payment_verifiers import BinancePayClient
from app.models import Payment, PaymentVerification, WebhookLog
from app.services.configuration import ConfigurationService
from app.infrastructure.redis_runtime import redis_runtime

router = APIRouter()


@router.post("/binance-pay", status_code=202)
async def binance_pay_webhook(request: Request, session: AsyncSession = Depends(db_session)) -> dict[str, str]:
    body = await request.body()
    timestamp = request.headers.get("Binancepay-Timestamp", "")
    nonce = request.headers.get("Binancepay-Nonce", "")
    signature = request.headers.get("Binancepay-Signature", "")
    configuration = await ConfigurationService(session).binance()
    valid = BinancePayClient(
        api_key=configuration.api_key,
        api_secret=configuration.api_secret,
        webhook_public_key=configuration.webhook_public_key,
        base_url=configuration.base_url,
    ).verify_webhook_signature(
        timestamp=timestamp,
        nonce=nonce,
        body=body,
        signature=signature,
    )
    valid = valid and _fresh_timestamp(timestamp)
    if valid and redis_runtime.client:
        nonce_key = f"ravenstore:webhooks:binance:nonce:{hash_secret(nonce)}"
        valid = bool(await redis_runtime.client.set(nonce_key, "1", ex=600, nx=True))
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="webhooks.invalid_payload") from exc
    data = payload.get("data") or {}
    event_id = str(payload.get("bizId") or data.get("transactionId") or hashlib.sha256(body).hexdigest())
    existing = await session.scalar(select(WebhookLog).where(WebhookLog.external_event_id == event_id))
    if existing:
        return {"message_key": "webhooks.already_processed"}
    log = WebhookLog(
        provider="binance_pay",
        event_type=str(payload.get("bizType") or "unknown"),
        external_event_id=event_id,
        payload_hash=hashlib.sha256(body).hexdigest(),
        signature_valid=valid,
        payload=payload,
    )
    session.add(log)
    if not valid:
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="webhooks.invalid_signature")
    merchant_trade_no = str(data.get("merchantTradeNo") or "")
    try:
        payment_id = UUID(hex=merchant_trade_no)
    except ValueError:
        log.processed_at = datetime.now(UTC)
        await session.commit()
        return {"message_key": "webhooks.accepted"}
    payment = await session.get(Payment, payment_id, with_for_update=True)
    if payment and payment.provider == "binance" and payment.status not in {"confirmed", "failed"}:
        verification = await session.scalar(
            select(PaymentVerification).where(PaymentVerification.payment_id == payment.id).with_for_update()
        )
        if verification:
            prepay_id = str(data.get("prepayId") or data.get("transactionId") or merchant_trade_no)
            verification.submitted_reference_encrypted = cipher.encrypt(prepay_id)
            verification.submitted_reference_hash = hash_secret(prepay_id)
            verification.verification_status = "queued"
            verification.next_attempt_at = datetime.now(UTC)
            verification.failure_code = None
    log.processed_at = datetime.now(UTC)
    await session.commit()
    return {"message_key": "webhooks.accepted"}


def _fresh_timestamp(value: str, tolerance_seconds: int = 300) -> bool:
    try:
        received = int(value) / 1000
    except (TypeError, ValueError):
        return False
    return abs(datetime.now(UTC).timestamp() - received) <= tolerance_seconds
