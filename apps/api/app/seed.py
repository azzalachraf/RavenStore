from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.i18n import load_translations
from app.models import Category, InventoryPool, Language, Permission, Product, ProductVariant, Role, TranslationKey, User
from app.core.config import settings
from app.core.security import hash_password
from app.services.inventory import InventoryService

ROLES = ["Owner", "Admin", "Moderator", "Support", "Customer"]
PERMISSIONS = [
    "products.read",
    "products.write",
    "orders.read",
    "orders.write",
    "payments.read",
    "payments.verify",
    "support.read",
    "support.write",
    "analytics.read",
    "settings.write",
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT pg_advisory_xact_lock(7271768376736564)"))
        existing_roles = set((await session.scalars(select(Role.name))).all())
        for role_name in ROLES:
            if role_name not in existing_roles:
                session.add(Role(name=role_name, description=f"{role_name} role", is_system=True))
        existing_permissions = set((await session.scalars(select(Permission.code))).all())
        for code in PERMISSIONS:
            if code not in existing_permissions:
                session.add(Permission(code=code, description=code))
        existing_languages = set((await session.scalars(select(Language.code))).all())
        existing_translations = set((await session.execute(select(TranslationKey.key, TranslationKey.language_code))).all())
        for code, name, rtl in [("en", "English", False), ("ar", "Arabic", True)]:
            if code not in existing_languages:
                session.add(Language(code=code, name=name, is_rtl=rtl, is_active=True))
            for key, value in load_translations(code).items():
                if (key, code) not in existing_translations:
                    session.add(TranslationKey(key=key, language_code=code, value=value))
        await session.flush()
        if settings.initial_owner_email and settings.initial_owner_password:
            owner = await session.scalar(select(User).where(User.email == settings.initial_owner_email.lower()))
            if owner is None:
                owner_role = await session.scalar(select(Role).where(Role.name == "Owner"))
                if owner_role is None:
                    raise RuntimeError("seed.owner_role_missing")
                session.add(
                    User(
                        email=settings.initial_owner_email.lower(),
                        password_hash=hash_password(settings.initial_owner_password.get_secret_value()),
                        display_name="RavenStore Owner",
                        role_id=owner_role.id,
                        status="active",
                        locale="en",
                    )
                )
        product_count = await session.scalar(select(Product.id).limit(1))
        if product_count is None:
            category = Category(
                slug="demo-digital-tools",
                name_key="categories.demo.name",
                description_key="categories.demo.description",
                sort_order=0,
                is_active=True,
            )
            session.add(category)
            await session.flush()
            product = Product(
                category_id=category.id,
                slug="ravenstore-demo-license",
                name_key="products.demo_license.name",
                description_key="products.demo_license.description",
                status="active",
                brand="RavenStore",
                product_metadata={
                    "featured": True,
                    "popular": True,
                    "warranty_days": 7,
                    "tags": ["demo", "license"],
                    "is_demo": True,
                },
            )
            session.add(product)
            await session.flush()
            variant = ProductVariant(
                product_id=product.id,
                sku="RAVEN-DEMO-LICENSE-30D",
                name_key="products.demo_license.variant",
                duration_days=30,
                region="global",
                delivery_type="license_key",
                price_amount=Decimal("1.00"),
                cost_amount=Decimal("0.00"),
                currency="USD",
                is_active=True,
            )
            session.add(variant)
            await session.flush()
            pool = InventoryPool(
                product_variant_id=variant.id,
                name="Demo license pool",
                delivery_type="license_key",
                priority=1,
                unlimited_stock=False,
                low_stock_threshold=3,
                is_active=True,
            )
            session.add(pool)
            await session.flush()
            await InventoryService(session).upload_assets(
                pool=pool,
                payloads=[f"RAVEN-DEMO-{uuid4().hex.upper()}" for _ in range(20)],
                metadata={"demo": True},
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
