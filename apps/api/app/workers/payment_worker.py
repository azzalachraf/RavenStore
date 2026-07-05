from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from time import perf_counter

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.observability import PAYMENT_VERIFICATIONS
from app.integrations.payment_verifiers import BinancePayClient, CryptoPaymentVerifier, VerificationResult
from app.models import Order, Payment, PaymentAttempt, PaymentVerification, Transaction
from app.services.configuration import ConfigurationService
from app.services.inventory import InventoryService
from app.services.payment_confirmation import PaymentConfirmationService
from app.services.outbox import OutboxService
from app.services.payments import payment_network_for_record


class PaymentWorker:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.configuration = ConfigurationService(session)
        self.crypto = CryptoPaymentVerifier()
        self.inventory = InventoryService(session)
        self.confirmation = PaymentConfirmationService(session)
        self.outbox = OutboxService(session)

    async def process_next(self) -> bool:
        verification = await self.session.scalar(
            select(PaymentVerification)
            .where(
                PaymentVerification.verification_status.in_(["queued", "retrying"]),
                (PaymentVerification.next_attempt_at.is_(None))
                | (PaymentVerification.next_attempt_at <= datetime.now(UTC)),
            )
            .order_by(PaymentVerification.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if verification is None:
            return False
        verification.verification_status = "processing"
        verification.locked_at = datetime.now(UTC)
        verification.attempt_count += 1
        verification.next_attempt_at = None
        verification_id = verification.id
        await self.session.commit()

        started = perf_counter()
        try:
            result = await self._verify(verification_id)
            duration_ms = int((perf_counter() - started) * 1000)
            await self._finalize(verification_id, result, duration_ms)
            PAYMENT_VERIFICATIONS.labels(result.status).inc()
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            await self.session.rollback()
            await self._record_failure(verification_id, exc, duration_ms)
            PAYMENT_VERIFICATIONS.labels("error").inc()
        return True

    async def _verify(self, verification_id) -> VerificationResult:
        verification = await self.session.get(PaymentVerification, verification_id)
        if verification is None:
            raise ValueError("payments.verification_not_found")
        payment = await self.session.get(Payment, verification.payment_id)
        if payment is None:
            raise ValueError("payments.not_found")
        configuration = await payment_network_for_record(self.configuration, payment)
        submitted_reference = (
            cipher.decrypt(verification.submitted_reference_encrypted)
            if verification.submitted_reference_encrypted
            else None
        )
        if payment.provider == "binance":
            binance_configuration = await self.configuration.binance()
            binance = BinancePayClient(
                api_key=binance_configuration.api_key,
                api_secret=binance_configuration.api_secret,
                webhook_public_key=binance_configuration.webhook_public_key,
                base_url=binance_configuration.base_url,
            )
            return await binance.verify_order(
                merchant_trade_no=payment.id.hex,
                expected_amount=payment.amount,
                submitted_reference=submitted_reference,
            )
        if not submitted_reference:
            raise ValueError("payments.reference_required")
        return await self.crypto.verify(
            configuration=configuration,
            tx_hash=submitted_reference,
            expected_amount=payment.amount,
        )

    async def _finalize(self, verification_id, result: VerificationResult, duration_ms: int) -> None:
        verification = await self.session.scalar(
            select(PaymentVerification).where(PaymentVerification.id == verification_id).with_for_update()
        )
        if verification is None:
            return
        payment = await self.session.get(Payment, verification.payment_id, with_for_update=True)
        if payment is None:
            raise ValueError("payments.not_found")
        if payment.status == "confirmed":
            verification.verification_status = "confirmed"
            verification.completed_at = datetime.now(UTC)
            verification.locked_at = None
            await self.session.commit()
            return
        reference_hash = verification.submitted_reference_hash or payment.payment_reference_hash
        await self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": reference_hash})
        duplicate = await self.session.scalar(
            select(Transaction.id).where(
                Transaction.network == payment.network,
                Transaction.reference_hash == reference_hash,
                Transaction.payment_id != payment.id,
            )
        )
        if duplicate:
            result = VerificationResult(
                matched=False,
                confirmations=result.confirmations,
                amount=result.amount,
                raw_payload=result.raw_payload,
                status="mismatched",
                failure_code="duplicate_payment_reference",
                provider_reference=result.provider_reference,
            )

        self.session.add(
            PaymentAttempt(
                payment_id=payment.id,
                verification_id=verification.id,
                source="verification_worker",
                status=result.status,
                submitted_reference_hash=reference_hash,
                failure_code=result.failure_code,
                risk_score=payment.risk_score,
                duration_ms=duration_ms,
                provider_response=result.raw_payload,
            )
        )
        if result.matched:
            await self._confirm(payment, verification, result, reference_hash)
        else:
            await self._schedule_or_escalate(payment, verification, result.failure_code or "payment_not_confirmed")
        await self.session.commit()

    async def _confirm(
        self,
        payment: Payment,
        verification: PaymentVerification,
        result: VerificationResult,
        reference_hash: str,
    ) -> None:
        await self.confirmation.confirm(
            payment=payment,
            verification=verification,
            result=result,
            reference_hash=reference_hash,
        )

    async def _schedule_or_escalate(
        self,
        payment: Payment,
        verification: PaymentVerification,
        failure_code: str,
    ) -> None:
        automation = await self.configuration.automation()
        terminal_review_codes = {
            "amount_underpaid",
            "amount_overpaid",
            "duplicate_payment_reference",
            "transfer_not_found",
        }
        expired = payment.expires_at <= datetime.now(UTC)
        exhausted = verification.attempt_count >= automation.verification_max_attempts
        if failure_code in terminal_review_codes:
            payment.status = "manual_review"
            payment.manual_review_reason = failure_code
            verification.verification_status = "manual_review"
            verification.next_attempt_at = None
            verification.completed_at = datetime.now(UTC)
            self.outbox.add(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type="payment.manual_review",
                payload={"payment_id": str(payment.id), "order_id": str(payment.order_id), "reason": failure_code},
            )
        elif expired or exhausted:
            payment.status = "failed"
            payment.failed_at = datetime.now(UTC)
            verification.verification_status = "failed"
            verification.completed_at = datetime.now(UTC)
            await self.inventory.release_for_order(payment.order_id, reason="payment_verification_failed")
            order = await self.session.get(Order, payment.order_id, with_for_update=True)
            if order:
                order.status = "payment_failed"
                self.outbox.add(
                    aggregate_type="order",
                    aggregate_id=order.id,
                    event_type="order.status_changed",
                    payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
                )
            self.outbox.add(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type="payment.failed",
                payload={"payment_id": str(payment.id), "order_id": str(payment.order_id), "reason": failure_code},
            )
        else:
            verification.verification_status = "retrying"
            delay = min(1800, (2 ** min(verification.attempt_count, 10)) * 15) + random.randint(0, 15)
            verification.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
        verification.failure_code = failure_code
        verification.locked_at = None

    async def _record_failure(self, verification_id, exc: Exception, duration_ms: int) -> None:
        verification = await self.session.scalar(
            select(PaymentVerification).where(PaymentVerification.id == verification_id).with_for_update()
        )
        if verification is None:
            return
        payment = await self.session.get(Payment, verification.payment_id, with_for_update=True)
        if payment is None:
            verification.verification_status = "failed"
            verification.last_error = "payments.not_found"
            verification.completed_at = datetime.now(UTC)
            await self.session.commit()
            return
        self.session.add(
            PaymentAttempt(
                payment_id=payment.id,
                verification_id=verification.id,
                source="verification_worker",
                status="error",
                submitted_reference_hash=verification.submitted_reference_hash,
                failure_code="provider_error",
                risk_score=payment.risk_score,
                duration_ms=duration_ms,
                provider_response={"error": str(exc)[:1000]},
            )
        )
        verification.last_error = str(exc)[:2000]
        await self._schedule_or_escalate(payment, verification, "provider_error")
        await self.session.commit()
