from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user, db_session
from app.models import Invoice, Order, Payment, PaymentAttempt, Receipt, Transaction, User
from app.schemas.payments import (
    InvoiceOut,
    PaymentAttemptOut,
    PaymentCreatedOut,
    PaymentOut,
    PaymentRequestIn,
    PaymentVerificationIn,
    ReceiptOut,
    TransactionOut,
)
from app.services.payments import PaymentService

router = APIRouter()


@router.post("/request", response_model=PaymentCreatedOut, status_code=201)
async def request_payment(
    payload: PaymentRequestIn,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    payment, token, reference = await PaymentService(session).create_payment(
        user_id=user.id,
        order_id=payload.order_id,
        method=payload.method,
    )
    return PaymentCreatedOut(payment=payment, payment_token=token, payment_reference=reference)


@router.post("/verify", status_code=202)
async def queue_payment_verification(payload: PaymentVerificationIn, session: AsyncSession = Depends(db_session)) -> dict:
    verification = await PaymentService(session).queue_verification(
        payment_token=payload.payment_token,
        submitted_reference=payload.submitted_reference,
    )
    return {"id": str(verification.id), "message_key": "payments.verification_queued"}


@router.get("", response_model=list[PaymentOut])
async def payment_history(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    result = await session.scalars(
        select(Payment)
        .join(Order, Order.id == Payment.order_id)
        .where(Order.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(min(max(limit, 1), 100))
        .offset(max(offset, 0))
    )
    return list(result.all())


@router.get("/{payment_id}/attempts", response_model=list[PaymentAttemptOut])
async def payment_attempts(
    payment_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    owned = await session.scalar(
        select(Payment.id).join(Order, Order.id == Payment.order_id).where(Payment.id == payment_id, Order.user_id == user.id)
    )
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="payments.not_found")
    result = await session.scalars(
        select(PaymentAttempt).where(PaymentAttempt.payment_id == payment_id).order_by(PaymentAttempt.created_at.desc())
    )
    return list(result.all())


@router.get("/{payment_id}/receipt", response_model=ReceiptOut)
async def payment_receipt(
    payment_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    receipt = await session.scalar(
        select(Receipt)
        .join(Payment, Payment.id == Receipt.payment_id)
        .join(Order, Order.id == Payment.order_id)
        .where(Receipt.payment_id == payment_id, Order.user_id == user.id)
    )
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="payments.receipt_not_found")
    return receipt


@router.get("/{payment_id}/transactions", response_model=list[TransactionOut])
async def payment_transactions(
    payment_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    owned = await session.scalar(
        select(Payment.id).join(Order, Order.id == Payment.order_id).where(Payment.id == payment_id, Order.user_id == user.id)
    )
    if not owned:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="payments.not_found")
    result = await session.scalars(
        select(Transaction).where(Transaction.payment_id == payment_id).order_by(Transaction.created_at.desc())
    )
    return list(result.all())


@router.get("/orders/{order_id}/invoice", response_model=InvoiceOut)
async def order_invoice(
    order_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    invoice = await session.scalar(
        select(Invoice).join(Order, Order.id == Invoice.order_id).where(Invoice.order_id == order_id, Order.user_id == user.id)
    )
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="payments.invoice_not_found")
    return invoice
