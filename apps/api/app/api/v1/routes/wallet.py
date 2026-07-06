from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import secrets

from app.core.dependencies import current_user, db_session
from app.models import (
    Category,
    Product,
    ProductVariant,
    Order,
    OrderItem,
    Inventory,
    User,
    Wallet,
)
from app.schemas.payments import WalletTopupRequest, PaymentCreatedOut
from app.services.payments import PaymentService

router = APIRouter()


@router.get("/summary")
async def wallet_summary(
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    # Get or create user wallet
    wallet = await session.scalar(select(Wallet).where(Wallet.user_id == user.id).with_for_update())
    if wallet is None:
        wallet = Wallet(user_id=user.id, balance=Decimal("0.00"))
        session.add(wallet)
        await session.flush()
        await session.commit()

    purchase_count = await session.scalar(select(func.count(Order.id)).where(Order.user_id == user.id))
    return {"purchase_count": purchase_count or 0, "future_balance": wallet.balance, "currency": "USD"}


@router.post("/topup", response_model=PaymentCreatedOut, status_code=201)
async def wallet_topup(
    payload: WalletTopupRequest,
    session: AsyncSession = Depends(db_session),
    user: User = Depends(current_user),
):
    # Find or create category
    category = await session.scalar(select(Category).where(Category.slug == "system"))
    if category is None:
        category = Category(slug="system", name_key="System Utilities", description_key="Internal system utilities")
        session.add(category)
        await session.flush()

    # Find or create product
    product = await session.scalar(select(Product).where(Product.slug == "wallet-topup"))
    if product is None:
        product = Product(category_id=category.id, slug="wallet-topup", name_key="Wallet Top-up", description_key="Credit user wallet balance")
        session.add(product)
        await session.flush()

    # Find or create variant
    variant = await session.scalar(select(ProductVariant).where(ProductVariant.sku == "wallet-topup-usd"))
    if variant is None:
        variant = ProductVariant(
            product_id=product.id,
            sku="wallet-topup-usd",
            name_key="Wallet Top-up USD",
            delivery_type="wallet_topup",
            price_amount=payload.amount,
            cost_amount=Decimal("0.00"),
            currency="USD",
            is_active=True
        )
        session.add(variant)
        await session.flush()

        inventory = Inventory(
            product_variant_id=variant.id,
            quantity_available=0,
            quantity_reserved=0,
            quantity_delivered=0,
            unlimited_stock=True,
        )
        session.add(inventory)
        await session.flush()
    else:
        # Update price to match requested amount
        variant.price_amount = payload.amount
        await session.flush()

    # Create the order
    order_number = f"RS-TOPUP-{secrets.token_hex(6).upper()}"
    order = Order(
        order_number=order_number,
        user_id=user.id,
        status="pending_payment",
        subtotal_amount=payload.amount,
        discount_amount=Decimal("0.00"),
        total_amount=payload.amount,
        cost_amount=Decimal("0.00"),
        currency="USD",
    )
    session.add(order)
    await session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_variant_id=variant.id,
        quantity=1,
        unit_price_amount=payload.amount,
        unit_cost_amount=Decimal("0.00"),
        snapshot={
            "sku": variant.sku,
            "name_key": variant.name_key,
            "delivery_type": variant.delivery_type,
            "currency": variant.currency,
        },
    )
    session.add(item)
    await session.flush()
    await session.commit()

    # Initiate payment request
    payment, token, reference = await PaymentService(session).create_payment(
        user_id=user.id,
        order_id=order.id,
        method=payload.method,
    )
    return PaymentCreatedOut(payment=payment, payment_token=token, payment_reference=reference)
