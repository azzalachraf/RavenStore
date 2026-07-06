from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Category, Product, ProductVariant
from app.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
)
from app.services.audit import AuditService
from app.services.outbox import OutboxService


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditService(session)
        self.outbox = OutboxService(session)

    async def categories(self, *, active_only: bool = True) -> list[Category]:
        statement = select(Category).order_by(Category.sort_order, Category.slug)
        if active_only:
            statement = statement.where(Category.is_active.is_(True))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def products(
        self,
        *,
        public_only: bool = True,
        limit: int = 50,
        offset: int = 0,
        category_id: UUID | None = None,
        search: str | None = None,
        catalog_filter: str | None = None,
    ) -> list[Product]:
        statement = select(Product).order_by(Product.created_at.desc()).limit(limit).offset(offset)
        if public_only:
            statement = statement.where(Product.status == "active")
        if category_id:
            statement = statement.where(Product.category_id == category_id)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(Product.slug.ilike(term), Product.name_key.ilike(term), Product.brand.ilike(term))
            )
        if catalog_filter in {"featured", "popular"}:
            statement = statement.where(Product.product_metadata[catalog_filter].as_boolean().is_(True))
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def product_by_slug(self, slug: str, *, public_only: bool = True) -> Product:
        statement = select(Product).where(Product.slug == slug)
        if public_only:
            statement = statement.where(Product.status == "active")
        result = await self.session.execute(statement)
        product = result.scalar_one_or_none()
        if product is None:
            raise AppError("products.not_found", status.HTTP_404_NOT_FOUND)
        return product

    async def create_category(self, payload: CategoryCreate, actor_id: UUID | None) -> Category:
        category = Category(**payload.model_dump())
        self.session.add(category)
        await self.session.flush()
        self.audit.log(actor_user_id=actor_id, action="category.create", resource_type="category", resource_id=category.id, metadata={})
        self.outbox.add(
            aggregate_type="category",
            aggregate_id=category.id,
            event_type="category.created",
            payload={"category_id": str(category.id), "slug": category.slug},
        )
        await self.session.commit()
        return category

    async def update_category(self, category_id: UUID, payload: CategoryUpdate, actor_id: UUID | None) -> Category:
        category = await self.session.get(Category, category_id, with_for_update=True)
        if category is None:
            raise AppError("categories.not_found", status.HTTP_404_NOT_FOUND)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(category, field, value)
        self.audit.log(actor_user_id=actor_id, action="category.update", resource_type="category", resource_id=category.id, metadata={"fields": list(changes)})
        self.outbox.add(
            aggregate_type="category",
            aggregate_id=category.id,
            event_type="category.updated",
            payload={"category_id": str(category.id), "fields": list(changes)},
        )
        await self.session.commit()
        return category

    async def delete_category(self, category_id: UUID, actor_id: UUID | None) -> Category:
        category = await self.session.get(Category, category_id, with_for_update=True)
        if category is None:
            raise AppError("categories.not_found", status.HTTP_404_NOT_FOUND)
        category.is_active = False
        self.audit.log(actor_user_id=actor_id, action="category.delete", resource_type="category", resource_id=category.id, metadata={})
        self.outbox.add(
            aggregate_type="category",
            aggregate_id=category.id,
            event_type="category.deleted",
            payload={"category_id": str(category.id)},
        )
        await self.session.commit()
        return category

    async def create_product(self, payload: ProductCreate, actor_id: UUID | None) -> Product:
        from app.core.crypto import cipher
        metadata = {**(payload.product_metadata or {})}
        delivery_content = metadata.pop("delivery_content", None)
        if delivery_content:
            metadata["delivery_content_encrypted"] = cipher.encrypt(str(delivery_content))
        payload.product_metadata = metadata

        product = Product(**payload.model_dump())
        self.session.add(product)
        await self.session.flush()
        self.audit.log(actor_user_id=actor_id, action="product.create", resource_type="product", resource_id=product.id, metadata={})
        self.outbox.add(
            aggregate_type="product",
            aggregate_id=product.id,
            event_type="product.created",
            payload={"product_id": str(product.id), "slug": product.slug},
        )
        await self.session.commit()
        return product

    async def update_product(self, product_id: UUID, payload: ProductUpdate, actor_id: UUID | None) -> Product:
        from app.core.crypto import cipher
        product = await self.session.get(Product, product_id, with_for_update=True)
        if product is None:
            raise AppError("products.not_found", status.HTTP_404_NOT_FOUND)
        changes = payload.model_dump(exclude_unset=True)
        expected_updated_at = changes.pop("expected_updated_at", None)
        if expected_updated_at and product.updated_at != expected_updated_at:
            raise AppError("products.concurrent_update", status.HTTP_409_CONFLICT)
        
        if "product_metadata" in changes and changes["product_metadata"] is not None:
            metadata = {**changes["product_metadata"]}
            if "delivery_content" in metadata:
                delivery_content = metadata.pop("delivery_content", None)
                if delivery_content:
                    metadata["delivery_content_encrypted"] = cipher.encrypt(str(delivery_content))
                else:
                    metadata.pop("delivery_content_encrypted", None)
            changes["product_metadata"] = metadata

        old_category_id = product.category_id
        for field, value in changes.items():
            setattr(product, field, value)
        self.audit.log(actor_user_id=actor_id, action="product.update", resource_type="product", resource_id=product.id, metadata={"fields": list(changes)})
        self.outbox.add(
            aggregate_type="product",
            aggregate_id=product.id,
            event_type="product.updated",
            payload={"product_id": str(product.id), "fields": list(changes)},
        )
        if "category_id" in changes and product.category_id != old_category_id:
            self.outbox.add(
                aggregate_type="product",
                aggregate_id=product.id,
                event_type="product.category_changed",
                payload={"product_id": str(product.id), "category_id": str(product.category_id)},
            )
        await self.session.commit()
        return product

    async def delete_product(self, product_id: UUID, actor_id: UUID | None) -> Product:
        product = await self.session.get(Product, product_id, with_for_update=True)
        if product is None:
            raise AppError("products.not_found", status.HTTP_404_NOT_FOUND)
        product.status = "archived"
        self.audit.log(actor_user_id=actor_id, action="product.delete", resource_type="product", resource_id=product.id, metadata={})
        self.outbox.add(
            aggregate_type="product",
            aggregate_id=product.id,
            event_type="product.deleted",
            payload={"product_id": str(product.id), "slug": product.slug},
        )
        await self.session.commit()
        return product

    async def create_variant(self, payload: ProductVariantCreate, actor_id: UUID | None) -> ProductVariant:
        product = await self.session.get(Product, payload.product_id)
        if product is None:
            raise AppError("products.not_found", status.HTTP_404_NOT_FOUND)
        variant = ProductVariant(**payload.model_dump())
        self.session.add(variant)
        await self.session.flush()
        self.audit.log(actor_user_id=actor_id, action="variant.create", resource_type="product_variant", resource_id=variant.id, metadata={})
        self.outbox.add(
            aggregate_type="product_variant",
            aggregate_id=variant.id,
            event_type="variant.created",
            payload={"variant_id": str(variant.id), "product_id": str(variant.product_id)},
        )
        await self.session.commit()
        return variant

    async def update_variant(self, variant_id: UUID, payload: ProductVariantUpdate, actor_id: UUID | None) -> ProductVariant:
        variant = await self.session.get(ProductVariant, variant_id, with_for_update=True)
        if variant is None:
            raise AppError("variants.not_found", status.HTTP_404_NOT_FOUND)
        changes = payload.model_dump(exclude_unset=True)
        old_price = variant.price_amount
        for field, value in changes.items():
            setattr(variant, field, value)
        self.audit.log(actor_user_id=actor_id, action="variant.update", resource_type="product_variant", resource_id=variant.id, metadata={"fields": list(changes)})
        self.outbox.add(
            aggregate_type="product_variant",
            aggregate_id=variant.id,
            event_type="variant.updated",
            payload={"variant_id": str(variant.id), "product_id": str(variant.product_id), "fields": list(changes)},
        )
        if "price_amount" in changes and variant.price_amount != old_price:
            self.outbox.add(
                aggregate_type="product",
                aggregate_id=variant.product_id,
                event_type="product.price_changed",
                payload={"product_id": str(variant.product_id), "variant_id": str(variant.id)},
            )
        await self.session.commit()
        return variant
