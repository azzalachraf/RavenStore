from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_session, require_roles
from app.core.crypto import cipher
from app.core.config import settings
from app.core.security import hash_secret
from app.integrations.payment_verifiers import VerificationResult
from app.models import (
    ActivityLog,
    DeliveryLog,
    DeliveryQueue,
    ErrorLog,
    FraudSignal,
    InventoryAsset,
    Inventory,
    InventoryPool,
    Order,
    Payment,
    PaymentAttempt,
    PaymentVerification,
    Product,
    ProductDownload,
    ProductImage,
    ProductVariant,
    SecurityEvent,
    StockHistory,
    Transaction,
    User,
    WebhookLog,
)
from app.schemas.automation import InventoryAdjustment, InventoryAssetUpload, InventoryPoolCreate, ManualPaymentApproval, ManualPaymentRejection
from app.schemas.catalog import ProductOut
from app.services.audit import AuditService
from app.services.inventory import ASSET_DELIVERY_TYPES, InventoryService
from app.services.catalog import CatalogService
from app.services.outbox import OutboxService
from app.services.payment_confirmation import PaymentConfirmationService
from app.services.uploads import UploadService, UploadValidationError
from app.infrastructure.redis_runtime import redis_runtime
from app.integrations.supabase_storage import SupabaseStorageClient

router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
async def products(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator", "Support")),
):
    return await CatalogService(session).products(public_only=False, limit=500)


@router.patch("/variants/{variant_id}/inventory")
async def adjust_inventory(
    variant_id: UUID,
    payload: InventoryAdjustment,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    variant = await session.get(ProductVariant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="products.variant_not_found")
    inventory = await session.scalar(
        select(Inventory).where(Inventory.product_variant_id == variant_id).with_for_update()
    )
    previous = inventory.quantity_available if inventory else 0
    if inventory is None:
        inventory = Inventory(product_variant_id=variant_id)
        session.add(inventory)
        await session.flush()
    inventory.quantity_available = payload.quantity_available
    inventory.unlimited_stock = payload.unlimited_stock
    inventory.low_stock_threshold = payload.low_stock_threshold
    inventory.is_active = True
    delta = payload.quantity_available - previous
    if delta:
        session.add(StockHistory(inventory_id=inventory.id, change=delta, reason="admin_adjustment", actor_user_id=admin.id))
    AuditService(session).log(
        actor_user_id=admin.id,
        action="inventory.adjust",
        resource_type="product_variant",
        resource_id=variant_id,
        metadata={"previous": previous, "available": payload.quantity_available, "unlimited": payload.unlimited_stock},
    )
    OutboxService(session).add(
        aggregate_type="product_variant",
        aggregate_id=variant_id,
        event_type="inventory.stock_changed",
        payload={"product_variant_id": str(variant_id), "reason": "admin_adjustment"},
        cache_tags=["products", f"product:{variant.product_id}"],
    )
    await session.commit()
    return {
        "product_variant_id": str(variant_id),
        "quantity_available": inventory.quantity_available,
        "unlimited_stock": inventory.unlimited_stock,
        "low_stock_threshold": inventory.low_stock_threshold,
    }


@router.get("/security/overview")
async def security_overview(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin")),
):
    since = datetime.now(UTC) - timedelta(hours=24)
    failed_logins = await session.scalar(
        select(func.count(SecurityEvent.id)).where(
            SecurityEvent.event_type == "auth.login_failed", SecurityEvent.created_at >= since
        )
    )
    suspicious = await session.scalar(
        select(func.count(SecurityEvent.id)).where(
            SecurityEvent.severity.in_(["high", "critical"]), SecurityEvent.created_at >= since
        )
    )
    webhook_failures = await session.scalar(
        select(func.count(WebhookLog.id)).where(WebhookLog.signature_valid.is_(False), WebhookLog.created_at >= since)
    )
    payment_anomalies = await session.scalar(
        select(func.count(FraudSignal.id)).where(FraudSignal.resolved_at.is_(None))
    )
    system_errors = await session.scalar(
        select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= since)
    )
    recent = await session.scalars(select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(50))
    metrics = await redis_runtime.metrics()
    workers = await redis_runtime.worker_health(["payment", "fulfillment", "notification", "outbox"])
    return {
        "window_hours": 24,
        "failed_logins": failed_logins or 0,
        "suspicious_events": suspicious or 0,
        "webhook_failures": webhook_failures or 0,
        "payment_anomalies": payment_anomalies or 0,
        "system_errors": system_errors or 0,
        "api_metrics": metrics.get("http", {}),
        "workers": workers,
        "recent_events": [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "severity": event.severity,
                "outcome": event.outcome,
                "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
                "trace_id": event.trace_id,
                "created_at": event.created_at,
            }
            for event in recent.all()
        ],
    }


@router.post("/uploads/quarantine", status_code=201)
async def quarantine_upload(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    try:
        artifact = await UploadService().quarantine(file)
    except UploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    AuditService(session).log(
        actor_user_id=admin.id,
        action="upload.quarantined",
        resource_type="upload",
        resource_id=None,
        metadata={
            "upload_id": artifact.upload_id,
            "filename": artifact.filename,
            "content_type": artifact.content_type,
            "size": artifact.size,
            "sha256": artifact.sha256,
            "scan_status": artifact.scan_status,
        },
    )
    await session.commit()
    return artifact


@router.post("/product-variants/{variant_id}/downloads", status_code=201)
async def upload_product_download(
    variant_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    variant = await session.get(ProductVariant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="products.variant_not_found")
    try:
        artifact = await UploadService().quarantine(
            file,
            bucket=settings.supabase_product_files_bucket,
            object_prefix=f"products/{variant.product_id}/{variant.id}",
        )
    except UploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if artifact.scan_status != "clean" or not artifact.storage_uri:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="uploads.antivirus_scan_required")
    download = ProductDownload(
        product_variant_id=variant.id,
        file_name=artifact.filename,
        storage_url_encrypted=cipher.encrypt(artifact.storage_uri),
        content_type=artifact.content_type,
    )
    session.add(download)
    AuditService(session).log(
        actor_user_id=admin.id,
        action="product.download_uploaded",
        resource_type="product_variant",
        resource_id=variant.id,
        metadata={"file_name": artifact.filename, "sha256": artifact.sha256, "size": artifact.size},
    )
    await session.commit()
    await session.refresh(download)
    return download


@router.post("/products/{product_id}/images", status_code=201)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="products.not_found")
    if (file.content_type or "").lower() not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="uploads.image_type_required")
    try:
        artifact = await UploadService().quarantine(
            file,
            bucket=settings.supabase_product_images_bucket,
            object_prefix=f"products/{product.id}",
        )
    except UploadValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if artifact.scan_status != "clean" or not artifact.storage_uri:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="uploads.antivirus_scan_required")
    bucket, object_path = SupabaseStorageClient().parse_uri(artifact.storage_uri)
    image = ProductImage(
        product_id=product.id,
        url=SupabaseStorageClient().public_url(bucket=bucket, object_path=object_path),
        alt_key=product.name_key,
        sort_order=len(product.images),
    )
    session.add(image)
    AuditService(session).log(
        actor_user_id=admin.id,
        action="product.image_uploaded",
        resource_type="product",
        resource_id=product.id,
        metadata={"file_name": artifact.filename, "sha256": artifact.sha256, "size": artifact.size},
    )
    OutboxService(session).add(
        aggregate_type="product",
        aggregate_id=product.id,
        event_type="product.updated",
        payload={"product_id": str(product.id), "reason": "image_uploaded"},
        cache_tags=["products", f"product:{product.slug}"],
    )
    await session.commit()
    await session.refresh(image)
    return image


@router.get("/orders")
async def orders(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator", "Support")),
):
    result = await session.execute(select(Order).order_by(Order.created_at.desc()).limit(200))
    return list(result.scalars().all())


@router.get("/payments")
async def payments(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator")),
):
    result = await session.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(200))
    return [
        {
            "id": str(payment.id),
            "order_id": str(payment.order_id),
            "provider": payment.provider,
            "network": payment.network,
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_address": payment.payment_address,
            "risk_score": payment.risk_score,
            "manual_review_reason": payment.manual_review_reason,
            "confirmed_at": payment.confirmed_at,
            "failed_at": payment.failed_at,
            "expires_at": payment.expires_at,
            "created_at": payment.created_at,
        }
        for payment in result.all()
    ]


@router.get("/delivery-queue")
async def delivery_queue(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Support")),
):
    result = await session.scalars(select(DeliveryQueue).order_by(DeliveryQueue.created_at.desc()).limit(200))
    return [
        {
            "id": str(delivery.id),
            "order_id": str(delivery.order_id),
            "order_item_id": str(delivery.order_item_id),
            "delivery_type": delivery.delivery_type,
            "provider_key": delivery.provider_key,
            "status": delivery.status,
            "attempt_count": delivery.attempt_count,
            "next_attempt_at": delivery.next_attempt_at,
            "completed_at": delivery.completed_at,
            "last_error": delivery.last_error,
            "created_at": delivery.created_at,
        }
        for delivery in result.all()
    ]


@router.get("/activity")
async def activity(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin")),
):
    result = await session.execute(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(200))
    return list(result.scalars().all())


@router.get("/users")
async def users(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Support")),
):
    result = await session.scalars(select(User).order_by(User.created_at.desc()).limit(200))
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role_id": str(user.role_id),
            "status": user.status,
            "locale": user.locale,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
        }
        for user in result.all()
    ]


@router.post("/inventory/pools", status_code=201)
async def create_inventory_pool(
    payload: InventoryPoolCreate,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    if payload.unlimited_stock and payload.delivery_type in ASSET_DELIVERY_TYPES and not payload.provider_key:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.unlimited_provider_required")
    if payload.delivery_type == "api_generated" and (not payload.unlimited_stock or not payload.provider_key):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.api_provider_required")
    pool = InventoryPool(**payload.model_dump())
    session.add(pool)
    await session.flush()
    inventory = await session.scalar(
        select(Inventory).where(Inventory.product_variant_id == pool.product_variant_id).with_for_update()
    )
    if inventory is None:
        inventory = Inventory(
            product_variant_id=pool.product_variant_id,
            quantity_available=0,
            quantity_reserved=0,
            quantity_delivered=0,
            unlimited_stock=pool.unlimited_stock,
        )
        session.add(inventory)
    elif pool.unlimited_stock:
        inventory.unlimited_stock = True
    AuditService(session).log(
        actor_user_id=admin.id,
        action="inventory.pool.create",
        resource_type="inventory_pool",
        resource_id=pool.id,
        metadata={"name": pool.name},
    )
    OutboxService(session).add(
        aggregate_type="inventory_pool",
        aggregate_id=pool.id,
        event_type="inventory.pool_created",
        payload={"pool_id": str(pool.id), "product_variant_id": str(pool.product_variant_id)},
    )
    await session.commit()
    await session.refresh(pool)
    return pool


@router.post("/inventory/pools/{pool_id}/assets", status_code=201)
async def upload_inventory_assets(
    pool_id: UUID,
    payload: InventoryAssetUpload,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    pool = await session.get(InventoryPool, pool_id, with_for_update=True)
    if pool is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="inventory.pool_not_found")
    created = await InventoryService(session).upload_assets(pool=pool, payloads=payload.payloads, metadata=payload.metadata)
    AuditService(session).log(
        actor_user_id=admin.id,
        action="inventory.assets.upload",
        resource_type="inventory_pool",
        resource_id=pool.id,
        metadata={"created": created, "submitted": len(payload.payloads)},
    )
    await session.commit()
    return {"created": created, "skipped": len(payload.payloads) - created}


@router.get("/inventory/pools")
async def inventory_pools(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator")),
):
    pools = list((await session.scalars(select(InventoryPool).order_by(InventoryPool.priority, InventoryPool.created_at))).all())
    output = []
    for pool in pools:
        counts = dict(
            (
                await session.execute(
                    select(InventoryAsset.status, func.count(InventoryAsset.id))
                    .where(InventoryAsset.pool_id == pool.id)
                    .group_by(InventoryAsset.status)
                )
            ).all()
        )
        output.append({
            "id": str(pool.id),
            "product_variant_id": str(pool.product_variant_id),
            "name": pool.name,
            "delivery_type": pool.delivery_type,
            "provider_key": pool.provider_key,
            "unlimited_stock": pool.unlimited_stock,
            "is_active": pool.is_active,
            "counts": counts,
        })
    return output


@router.post("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: UUID,
    payload: ManualPaymentApproval,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    payment = await session.get(Payment, payment_id, with_for_update=True)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="payments.not_found")
    if payment.status == "confirmed":
        return {"message_key": "payments.already_confirmed"}
    if payment.status != "manual_review":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="payments.not_in_manual_review")
    if Decimal(payload.confirmed_amount) != Decimal(payment.amount):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payments.amount_mismatch")
    reference_hash = hash_secret(payload.reference.strip())
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": reference_hash})
    duplicate = await session.scalar(
        select(Transaction.id).where(Transaction.network == payment.network, Transaction.reference_hash == reference_hash)
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="payments.duplicate_reference")
    verification = await session.scalar(
        select(PaymentVerification).where(PaymentVerification.payment_id == payment.id).with_for_update()
    )
    if verification is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="payments.verification_not_found")
    result = VerificationResult(
        matched=True,
        confirmations=0,
        amount=payment.amount,
        raw_payload={"manual_review_note": payload.note},
        status="confirmed",
        provider_reference=payload.reference.strip(),
    )
    await PaymentConfirmationService(session).confirm(
        payment=payment,
        verification=verification,
        result=result,
        reference_hash=reference_hash,
        source="manual_review",
        actor_user_id=admin.id,
    )
    AuditService(session).log(
        actor_user_id=admin.id,
        action="payment.manual_approve",
        resource_type="payment",
        resource_id=payment.id,
        metadata={"note": payload.note},
    )
    await session.commit()
    return {"message_key": "payments.approved"}


@router.post("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: UUID,
    payload: ManualPaymentRejection,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin")),
):
    payment = await session.get(Payment, payment_id, with_for_update=True)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="payments.not_found")
    if payment.status == "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="payments.already_confirmed")
    payment.status = "failed"
    payment.failed_at = datetime.now(UTC)
    payment.manual_review_reason = payload.reason
    order = await session.get(Order, payment.order_id, with_for_update=True)
    if order:
        order.status = "payment_failed"
        OutboxService(session).add(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.status_changed",
            payload={"order_id": str(order.id), "user_id": str(order.user_id), "status": order.status},
        )
    await InventoryService(session).release_for_order(payment.order_id, reason="manual_payment_rejection")
    OutboxService(session).add(
        aggregate_type="payment",
        aggregate_id=payment.id,
        event_type="payment.failed",
        payload={"payment_id": str(payment.id), "order_id": str(payment.order_id), "reason": payload.reason},
    )
    AuditService(session).log(
        actor_user_id=admin.id,
        action="payment.manual_reject",
        resource_type="payment",
        resource_id=payment.id,
        metadata={"reason": payload.reason},
    )
    await session.commit()
    return {"message_key": "payments.rejected"}


@router.post("/deliveries/{delivery_id}/retry", status_code=202)
async def retry_delivery(
    delivery_id: UUID,
    session: AsyncSession = Depends(db_session),
    admin: User = Depends(require_roles("Owner", "Admin", "Support")),
):
    delivery = await session.get(DeliveryQueue, delivery_id, with_for_update=True)
    if delivery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="delivery.not_found")
    if delivery.status == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="delivery.already_completed")
    delivery.status = "queued"
    delivery.next_attempt_at = datetime.now(UTC)
    delivery.last_error = None
    AuditService(session).log(
        actor_user_id=admin.id,
        action="delivery.retry",
        resource_type="delivery",
        resource_id=delivery.id,
        metadata={},
    )
    await session.commit()
    return {"message_key": "delivery.retry_queued"}


@router.get("/payments/{payment_id}/attempts")
async def admin_payment_attempts(
    payment_id: UUID,
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator")),
):
    attempts = await session.scalars(
        select(PaymentAttempt).where(PaymentAttempt.payment_id == payment_id).order_by(PaymentAttempt.created_at.desc())
    )
    return [
        {
            "id": str(attempt.id),
            "source": attempt.source,
            "status": attempt.status,
            "failure_code": attempt.failure_code,
            "risk_score": attempt.risk_score,
            "duration_ms": attempt.duration_ms,
            "created_at": attempt.created_at,
        }
        for attempt in attempts.all()
    ]


@router.get("/deliveries/{delivery_id}/logs")
async def admin_delivery_logs(
    delivery_id: UUID,
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Support")),
):
    logs = await session.scalars(
        select(DeliveryLog).where(DeliveryLog.delivery_id == delivery_id).order_by(DeliveryLog.created_at.desc())
    )
    return list(logs.all())
