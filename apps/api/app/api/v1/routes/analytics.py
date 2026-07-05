from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_session, require_roles
from app.schemas.misc import AnalyticsSummaryOut
from app.models import AnalyticsDailyMetric
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryOut)
async def summary(
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator")),
):
    return await AnalyticsService(session).summary()


@router.get("/payment-automation")
async def payment_automation_metrics(
    metric_date: date | None = None,
    session: AsyncSession = Depends(db_session),
    _=Depends(require_roles("Owner", "Admin", "Moderator")),
):
    selected_date = metric_date or date.today()
    rows = await session.execute(
        select(AnalyticsDailyMetric.metric_key, AnalyticsDailyMetric.value).where(
            AnalyticsDailyMetric.metric_date == selected_date,
            AnalyticsDailyMetric.metric_key.in_(
                [
                    "payment_success_rate",
                    "failed_payments",
                    "abandoned_checkouts",
                    "average_order_value",
                    "average_delivery_seconds",
                    "inventory_delivered",
                    "inventory_available",
                ]
            ),
        )
    )
    return {"date": selected_date, "metrics": dict(rows.all())}
