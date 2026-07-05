from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.errors import AppError
from app.core.security import hash_secret
from app.models import (
    Inventory,
    InventoryAsset,
    InventoryPool,
    InventoryReservation,
    Order,
    OrderItem,
    StockHistory,
)
from app.services.outbox import OutboxService

ASSET_DELIVERY_TYPES = {"account", "credentials", "invite_link", "license_key", "activation_code"}


class InventoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.outbox = OutboxService(session)

    async def reserve(self, *, order: Order, item: OrderItem, reservation_minutes: int) -> InventoryReservation | None:
        existing = await self.session.scalar(
            select(InventoryReservation).where(InventoryReservation.order_item_id == item.id).with_for_update()
        )
        if existing:
            return existing

        pools = list(
            (
                await self.session.scalars(
                    select(InventoryPool)
                    .where(InventoryPool.product_variant_id == item.product_variant_id, InventoryPool.is_active.is_(True))
                    .order_by(InventoryPool.priority, InventoryPool.created_at)
                    .with_for_update()
                )
            ).all()
        )
        legacy = await self.session.scalar(
            select(Inventory).where(Inventory.product_variant_id == item.product_variant_id).with_for_update()
        )
        if not pools and legacy is None:
            if item.snapshot.get("delivery_type") in ASSET_DELIVERY_TYPES:
                raise AppError("inventory.pool_required", status.HTTP_409_CONFLICT)
            return None

        expires_at = datetime.now(UTC) + timedelta(minutes=reservation_minutes)
        pool: InventoryPool | None = None
        asset: InventoryAsset | None = None
        for candidate in pools:
            if candidate.unlimited_stock:
                pool = candidate
                break
            if item.quantity != 1:
                raise AppError("inventory.asset_quantity_must_be_one", status.HTTP_422_UNPROCESSABLE_ENTITY)
            candidate_asset = await self.session.scalar(
                select(InventoryAsset)
                .where(
                    InventoryAsset.pool_id == candidate.id,
                    InventoryAsset.status == "available",
                    or_(InventoryAsset.expires_at.is_(None), InventoryAsset.expires_at > datetime.now(UTC)),
                )
                .order_by(InventoryAsset.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if candidate_asset:
                pool = candidate
                asset = candidate_asset
                break
        if pools and pool is None:
            raise AppError("inventory.insufficient_stock", status.HTTP_409_CONFLICT)
        unlimited = bool((pool and pool.unlimited_stock) or (legacy and legacy.unlimited_stock))
        if asset:
            asset.status = "reserved"
            asset.reserved_order_id = order.id
            asset.reserved_order_item_id = item.id
            asset.reserved_at = datetime.now(UTC)

        if legacy and not unlimited:
            if legacy.quantity_available < item.quantity:
                raise AppError("inventory.insufficient_stock", status.HTTP_409_CONFLICT)
            legacy.quantity_available -= item.quantity
            legacy.quantity_reserved += item.quantity
            self.session.add(
                StockHistory(inventory_id=legacy.id, change=-item.quantity, reason="checkout_reserved")
            )

        reservation = InventoryReservation(
            order_id=order.id,
            order_item_id=item.id,
            pool_id=pool.id if pool else None,
            asset_id=asset.id if asset else None,
            quantity=item.quantity,
            status="reserved",
            expires_at=expires_at,
        )
        self.session.add(reservation)
        if pool and not unlimited:
            await self._emit_low_stock(pool)
        self._stock_changed(
            variant_id=item.product_variant_id,
            reason="checkout_reserved",
            order_id=order.id,
        )
        return reservation

    async def commit_for_order(self, order_id: UUID) -> None:
        reservations = list(
            (
                await self.session.scalars(
                    select(InventoryReservation)
                    .where(InventoryReservation.order_id == order_id, InventoryReservation.status == "reserved")
                    .with_for_update()
                )
            ).all()
        )
        for reservation in reservations:
            reservation.status = "committed"
            item = await self.session.get(OrderItem, reservation.order_item_id)
            if item:
                self._stock_changed(variant_id=item.product_variant_id, reason="reservation_committed", order_id=order_id)

    async def release_for_order(self, order_id: UUID, *, reason: str) -> int:
        reservations = list(
            (
                await self.session.scalars(
                    select(InventoryReservation)
                    .where(
                        InventoryReservation.order_id == order_id,
                        InventoryReservation.status.in_(["reserved", "committed"]),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for reservation in reservations:
            await self._release(reservation, reason=reason)
        return len(reservations)

    async def release_expired(self) -> int:
        reservations = list(
            (
                await self.session.scalars(
                    select(InventoryReservation)
                    .where(
                        InventoryReservation.status == "reserved",
                        InventoryReservation.expires_at < datetime.now(UTC),
                    )
                    .limit(500)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for reservation in reservations:
            await self._release(reservation, reason="checkout_expired")
        return len(reservations)

    async def mark_delivered(self, reservation: InventoryReservation) -> None:
        if reservation.status == "delivered":
            return
        reservation.status = "delivered"
        if reservation.asset_id:
            asset = await self.session.get(InventoryAsset, reservation.asset_id, with_for_update=True)
            if asset:
                asset.status = "delivered"
                asset.delivered_at = datetime.now(UTC)
        item = await self.session.get(OrderItem, reservation.order_item_id)
        if item:
            legacy = await self.session.scalar(
                select(Inventory).where(Inventory.product_variant_id == item.product_variant_id).with_for_update()
            )
            if legacy and not legacy.unlimited_stock:
                legacy.quantity_reserved = max(0, legacy.quantity_reserved - reservation.quantity)
                legacy.quantity_delivered += reservation.quantity
            self._stock_changed(
                variant_id=item.product_variant_id,
                reason="inventory_delivered",
                order_id=item.order_id,
            )

    async def upload_assets(self, *, pool: InventoryPool, payloads: list[str], metadata: dict | None = None) -> int:
        created = 0
        for raw in payloads:
            value = raw.strip()
            if not value:
                continue
            fingerprint = hash_secret(value)
            exists = await self.session.scalar(
                select(InventoryAsset.id).where(
                    InventoryAsset.pool_id == pool.id,
                    InventoryAsset.payload_fingerprint == fingerprint,
                )
            )
            if exists:
                continue
            self.session.add(
                InventoryAsset(
                    pool_id=pool.id,
                    payload_encrypted=cipher.encrypt(value),
                    payload_fingerprint=fingerprint,
                    status="available",
                    asset_metadata=metadata or {},
                )
            )
            created += 1
        if created:
            inventory = await self.session.scalar(
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
                self.session.add(inventory)
            if not pool.unlimited_stock:
                inventory.quantity_available += created
            inventory.unlimited_stock = pool.unlimited_stock
            self._stock_changed(variant_id=pool.product_variant_id, reason="assets_uploaded")
        return created

    async def _release(self, reservation: InventoryReservation, *, reason: str) -> None:
        reservation.status = "released"
        reservation.released_at = datetime.now(UTC)
        if reservation.asset_id:
            asset = await self.session.get(InventoryAsset, reservation.asset_id, with_for_update=True)
            if asset and asset.status == "reserved":
                asset.status = "available"
                asset.reserved_order_id = None
                asset.reserved_order_item_id = None
                asset.reserved_at = None
        item = await self.session.get(OrderItem, reservation.order_item_id)
        if item:
            legacy = await self.session.scalar(
                select(Inventory).where(Inventory.product_variant_id == item.product_variant_id).with_for_update()
            )
            if legacy and not legacy.unlimited_stock:
                legacy.quantity_reserved = max(0, legacy.quantity_reserved - reservation.quantity)
                legacy.quantity_available += reservation.quantity
                self.session.add(
                    StockHistory(inventory_id=legacy.id, change=reservation.quantity, reason=reason)
                )
            self._stock_changed(variant_id=item.product_variant_id, reason=reason, order_id=item.order_id)

    async def _emit_low_stock(self, pool: InventoryPool) -> None:
        count = await self.session.scalar(
            select(func.count(InventoryAsset.id)).where(
                InventoryAsset.pool_id == pool.id,
                InventoryAsset.status == "available",
            )
        )
        if (count or 0) <= pool.low_stock_threshold:
            self.outbox.add(
                aggregate_type="inventory_pool",
                aggregate_id=pool.id,
                event_type="inventory.low_stock",
                payload={"pool_id": str(pool.id), "available": count or 0},
            )

    def _stock_changed(self, *, variant_id: UUID, reason: str, order_id: UUID | None = None) -> None:
        self.outbox.add(
            aggregate_type="product_variant",
            aggregate_id=variant_id,
            event_type="inventory.stock_changed",
            payload={
                "product_variant_id": str(variant_id),
                "reason": reason,
                "order_id": str(order_id) if order_id else None,
            },
        )
