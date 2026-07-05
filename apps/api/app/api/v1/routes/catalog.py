from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_session, require_roles
from app.models import User
from app.schemas.catalog import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantOut,
    ProductVariantUpdate,
)
from app.services.catalog import CatalogService

router = APIRouter()
category_router = APIRouter()


@router.get("", response_model=list[ProductOut])
async def list_products(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: UUID | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=120),
    filter: str | None = Query(default=None, pattern="^(featured|popular|newest)$"),
    session: AsyncSession = Depends(db_session),
) -> list:
    return await CatalogService(session).products(
        public_only=True,
        limit=limit,
        offset=offset,
        category_id=category_id,
        search=search,
        catalog_filter=filter,
    )


@router.get("/{slug}", response_model=ProductOut)
async def product_detail(slug: str, session: AsyncSession = Depends(db_session)):
    return await CatalogService(session).product_by_slug(slug, public_only=True)


@category_router.get("", response_model=list[CategoryOut])
async def list_categories(session: AsyncSession = Depends(db_session)) -> list:
    return await CatalogService(session).categories(active_only=True)


@category_router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    payload: CategoryCreate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).create_category(payload, user.id)


@category_router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).update_category(category_id, payload, user.id)


@category_router.delete("/{category_id}", response_model=CategoryOut)
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).delete_category(category_id, user.id)


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).create_product(payload, user.id)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).update_product(product_id, payload, user.id)


@router.delete("/{product_id}", response_model=ProductOut)
async def delete_product(
    product_id: UUID,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).delete_product(product_id, user.id)


@router.post("/variants", response_model=ProductVariantOut, status_code=201)
async def create_variant(
    payload: ProductVariantCreate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).create_variant(payload, user.id)


@router.patch("/variants/{variant_id}", response_model=ProductVariantOut)
async def update_variant(
    variant_id: UUID,
    payload: ProductVariantUpdate,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(require_roles("Owner", "Admin")),
):
    return await CatalogService(session).update_variant(variant_id, payload, user.id)
