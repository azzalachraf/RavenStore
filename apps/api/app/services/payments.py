from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.errors import AppError
from app.core.security import generate_public_token, hash_secret
from app.integrations.payment_verifiers import BinancePayClient
from app.models import Order, Payment, PaymentAttempt, PaymentVerification
from app.services.audit import AuditService
from app.services.configuration import ConfigurationService, NetworkConfiguration
from app.services.fraud import FraudService
from app.services.ledger import LedgerService
from app.services.outbox import OutboxService


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditService(session)
        self.configuration = ConfigurationService(session)
        self.outbox = OutboxService(session)
        self.ledger = LedgerService(session)
        self.fraud = FraudService(session)

    async def create_payment(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        method: str,
    ) -> tuple[Payment, str, str]:
        try:
            network = await self.configuration.payment_network(method)
        except ValueError as exc:
            raise AppError("payments.unsupported_method", status.HTTP_400_BAD_REQUEST) from exc
        if not network.enabled:
            raise AppError("payments.method_disabled", status.HTTP_409_CONFLICT)
        if network.provider == "crypto" and (not network.address or not network.contract_address):
            raise AppError("payments.network_not_configured", status.HTTP_503_SERVICE_UNAVAILABLE)
        order = await self.session.get(Order, order_id)
        if order is None or order.user_id != user_id:
            raise AppError("orders.not_found", status.HTTP_404_NOT_FOUND)
        if order.status not in {"pending_payment", "payment_failed"}:
            raise AppError("payments.order_not_payable", status.HTTP_409_CONFLICT)
        automation = await self.configuration.automation()
        result = await self.session.execute(select(Payment).where(Payment.order_id == order_id).with_for_update())
        payment = result.scalar_one_or_none()
        previous_network = payment.network if payment else None
        token = generate_public_token("pay")
        if payment is None:
            reference = f"RS-{order.order_number.replace('-', '')}-{secrets.token_hex(8).upper()}"
            payment = Payment(
                order_id=order.id,
                provider=network.provider,
                network=network.network,
                status="pending",
                amount=Decimal(order.total_amount).quantize(Decimal("0.00000001")),
                currency=network.currency,
                payment_address=network.address,
                payment_reference_encrypted=cipher.encrypt(reference),
                payment_reference_hash=hash_secret(reference),
                payment_token_hash=hash_secret(token),
                expires_at=datetime.now(UTC) + timedelta(minutes=automation.payment_expiry_minutes),
            )
            self.session.add(payment)
            await self.session.flush()
            verification = PaymentVerification(payment_id=payment.id, verification_status="awaiting_reference")
            self.session.add(verification)
        else:
            reference = cipher.decrypt(payment.payment_reference_encrypted)
            payment.provider = network.provider
            payment.network = network.network
            payment.currency = network.currency
            payment.payment_address = network.address
            payment.payment_token_hash = hash_secret(token)
            payment.expires_at = datetime.now(UTC) + timedelta(minutes=automation.payment_expiry_minutes)
            payment.status = "pending"
            payment.failed_at = None
            payment.manual_review_reason = None
            verification_result = await self.session.execute(
                select(PaymentVerification).where(PaymentVerification.payment_id == payment.id).with_for_update()
            )
            verification = verification_result.scalar_one_or_none()
            if verification:
                verification.verification_status = "awaiting_reference"
                verification.next_attempt_at = None
                verification.completed_at = None
                verification.failure_code = None
                verification.last_error = None
        if network.provider == "binance":
            if payment.provider_order_id_encrypted is None or previous_network != network.network:
                try:
                    await self._create_binance_request(payment, order)
                except (ValueError, httpx.HTTPError) as exc:
                    raise AppError("payments.provider_unavailable", status.HTTP_503_SERVICE_UNAVAILABLE) from exc
            verification_result = await self.session.execute(
                select(PaymentVerification).where(PaymentVerification.payment_id == payment.id)
            )
            verification = verification_result.scalar_one_or_none()
            if verification:
                verification.verification_status = "queued"
                verification.next_attempt_at = datetime.now(UTC)
        elif network.provider == "wallet":
            from app.models import Wallet, WalletTransaction, Transaction
            wallet_result = await self.session.execute(
                select(Wallet).where(Wallet.user_id == user_id).with_for_update()
            )
            user_wallet = wallet_result.scalar_one_or_none()
            if user_wallet is None:
                user_wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
                self.session.add(user_wallet)
                await self.session.flush()

            if user_wallet.balance < order.total_amount:
                raise AppError("payments.insufficient_wallet_balance", status.HTTP_400_BAD_REQUEST)

            user_wallet.balance -= order.total_amount

            wallet_tx = WalletTransaction(
                wallet_id=user_wallet.id,
                amount=-order.total_amount,
                type="purchase",
                description=f"Purchase of order {order.order_number}",
                reference_id=order.id
            )
            self.session.add(wallet_tx)

            payment.status = "confirmed"
            payment.confirmed_at = datetime.now(UTC)
            payment.expires_at = datetime.now(UTC)

            order.status = "paid"

            verification_result = await self.session.execute(
                select(PaymentVerification).where(PaymentVerification.payment_id == payment.id).with_for_update()
            )
            verification = verification_result.scalar_one_or_none()
            if verification:
                verification.verification_status = "confirmed"
                verification.completed_at = datetime.now(UTC)

            transaction = Transaction(
                payment_id=payment.id,
                tx_hash=reference,
                reference_hash=hash_secret(reference),
                amount=order.total_amount,
                currency="USD",
                network="WALLET",
                confirmations=1,
                status="confirmed",
                raw_payload={"source": "wallet"},
            )
            self.session.add(transaction)
            await self.session.flush()

            from app.services.inventory import InventoryService
            await InventoryService(self.session).commit_for_order(order.id)

            await self.ledger.ensure_receipt(payment, transaction)
            await self.ledger.ensure_invoice(order)

            from app.services.fulfillment import FulfillmentService
            await FulfillmentService(self.session).enqueue_paid_order(order)

            self.outbox.add(
                aggregate_type="order",
                aggregate_id=order.id,
                event_type="order.status_changed",
                payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
            )
            self.outbox.add(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type="payment.confirmed",
                payload={"payment_id": str(payment.id), "order_id": str(order.id), "user_id": str(order.user_id)},
            )

            self.audit.log(
                actor_user_id=user_id,
                action="payment.wallet_checkout",
                resource_type="order",
                resource_id=order.id,
                metadata={"amount": str(order.total_amount), "wallet_id": str(user_wallet.id)}
            )

            await self.session.commit()
            return payment, token, reference
        else:
            payment.provider_order_id_encrypted = None
            payment.payment_url = None
        await self.ledger.ensure_invoice(order)
        self.outbox.add(
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type="payment.created",
            payload={"payment_id": str(payment.id), "order_id": str(order.id), "user_id": str(user_id), "network": payment.network},
        )
        self.audit.log(
            actor_user_id=user_id,
            action="payment.create",
            resource_type="payment",
            resource_id=payment.id,
            metadata={"method": method, "order_number": order.order_number},
        )
        await self.session.commit()
        await self.session.refresh(payment)
        return payment, token, reference

    async def queue_verification(
        self,
        *,
        payment_token: str,
        submitted_reference: str | None,
    ) -> PaymentVerification:
        if not submitted_reference or len(submitted_reference.strip()) < 6:
            raise AppError("payments.reference_required", status.HTTP_422_UNPROCESSABLE_ENTITY)
        result = await self.session.execute(
            select(Payment).where(Payment.payment_token_hash == hash_secret(payment_token)).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise AppError("payments.not_found", status.HTTP_404_NOT_FOUND)
        if payment.status == "confirmed":
            result = await self.session.execute(select(PaymentVerification).where(PaymentVerification.payment_id == payment.id))
            return result.scalar_one()
        automation = await self.configuration.automation()
        reference = submitted_reference.strip()
        reference_hash = hash_secret(reference)
        assessment = await self.fraud.assess_submission(
            payment=payment,
            reference_hash=reference_hash,
            automation=automation,
        )
        result = await self.session.execute(
            select(PaymentVerification).where(PaymentVerification.payment_id == payment.id).with_for_update()
        )
        verification = result.scalar_one_or_none()
        if verification is None:
            verification = PaymentVerification(payment_id=payment.id)
            self.session.add(verification)
            await self.session.flush()
        verification.submitted_tx_hash = None
        verification.submitted_reference_encrypted = cipher.encrypt(reference)
        verification.submitted_reference_hash = reference_hash
        verification.failure_code = None
        verification.last_error = None
        payment.risk_score = assessment.score
        if assessment.score >= automation.fraud_score_threshold:
            payment.status = "manual_review"
            payment.manual_review_reason = assessment.signals[0][0] if assessment.signals else "fraud_score_threshold"
            verification.verification_status = "manual_review"
            verification.next_attempt_at = None
        else:
            verification.verification_status = "queued"
            verification.next_attempt_at = datetime.now(UTC)
        self.session.add(
            PaymentAttempt(
                payment_id=payment.id,
                verification_id=verification.id,
                source="customer_submission",
                status=verification.verification_status,
                submitted_reference_hash=reference_hash,
                risk_score=assessment.score,
                provider_response={},
            )
        )
        self.outbox.add(
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type="payment.verification_requested",
            payload={"payment_id": str(payment.id), "order_id": str(payment.order_id), "risk_score": assessment.score},
        )
        await self.session.commit()
        return verification

    async def _create_binance_request(self, payment: Payment, order: Order) -> None:
        configuration = await self.configuration.binance()
        binance = BinancePayClient(
            api_key=configuration.api_key,
            api_secret=configuration.api_secret,
            webhook_public_key=configuration.webhook_public_key,
            base_url=configuration.base_url,
        )
        merchant_trade_no = payment.id.hex
        response = await binance.create_order(
            merchant_trade_no=merchant_trade_no,
            amount=payment.amount,
            currency=payment.currency,
            product_name=f"RavenStore {order.order_number}",
        )
        data = response.get("data") or {}
        provider_order_id = str(data.get("prepayId") or merchant_trade_no)
        payment.provider_order_id_encrypted = cipher.encrypt(provider_order_id)
        payment.payment_url = data.get("checkoutUrl") or data.get("universalUrl") or data.get("qrcodeLink")


async def payment_network_for_record(
    service: ConfigurationService,
    payment: Payment,
) -> NetworkConfiguration:
    method = {"USDT_TRC20": "usdt_trc20", "USDT_BEP20": "usdt_bep20", "BINANCE": "binance"}.get(payment.network)
    if not method:
        raise ValueError("payments.unsupported_method")
    return await service.payment_network(method)
