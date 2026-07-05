from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import admin, analytics, auth, catalog, events, languages, notifications, orders, payments, referrals, settings, support, telegram, users, wallet, webhooks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(catalog.router, prefix="/products", tags=["products"])
api_router.include_router(catalog.category_router, prefix="/categories", tags=["categories"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(languages.router, prefix="/languages", tags=["languages"])
api_router.include_router(referrals.router, prefix="/referral", tags=["referral"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
