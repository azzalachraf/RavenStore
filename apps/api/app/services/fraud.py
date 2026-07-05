from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FraudSignal, Payment, PaymentAttempt, PaymentVerification, Transaction
from app.services.configuration import AutomationConfiguration


class FraudAssessment:
    def __init__(self, score: int, signals: list[tuple[str, str, dict]]):
        self.score = min(score, 100)
        self.signals = signals


class FraudService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def assess_submission(
        self,
        *,
        payment: Payment,
        reference_hash: str,
        automation: AutomationConfiguration,
    ) -> FraudAssessment:
        score = 0
        signals: list[tuple[str, str, dict]] = []
        duplicate_transaction = await self.session.scalar(
            select(func.count(Transaction.id)).where(Transaction.network == payment.network, Transaction.reference_hash == reference_hash)
        )
        duplicate_claim = await self.session.scalar(
            select(func.count(PaymentVerification.id)).where(
                PaymentVerification.submitted_reference_hash == reference_hash,
                PaymentVerification.payment_id != payment.id,
            )
        )
        if duplicate_transaction or duplicate_claim:
            score += 100
            signals.append(("duplicate_payment_reference", "critical", {}))
        if payment.expires_at < datetime.now(UTC):
            score += 30
            signals.append(("expired_checkout_submission", "medium", {"expired_at": payment.expires_at.isoformat()}))
        if Decimal(payment.amount) >= automation.manual_review_amount:
            score += 20
            signals.append(("high_value_payment", "low", {"amount": str(payment.amount)}))
        attempts = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(PaymentAttempt.payment_id == payment.id)
        )
        if (attempts or 0) > 5:
            score += 20
            signals.append(("excessive_verification_attempts", "medium", {"attempts": attempts}))
        for code, severity, details in signals:
            self.session.add(FraudSignal(payment_id=payment.id, code=code, severity=severity, details=details))
        return FraudAssessment(score, signals)

    async def mark_resolved(self, signal_id: UUID) -> None:
        signal = await self.session.get(FraudSignal, signal_id)
        if signal:
            signal.resolved_at = datetime.now(UTC)
