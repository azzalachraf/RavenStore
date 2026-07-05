from __future__ import annotations

import asyncio
import time

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.core.observability import WORKER_HEARTBEAT, WORKER_JOBS
from app.infrastructure.redis_runtime import redis_runtime
from app.services.fulfillment import FulfillmentService
from app.workers.analytics_worker import AnalyticsWorker
from app.workers.backup_worker import BackupWorker
from app.workers.cleanup_worker import CleanupWorker
from app.workers.notification_worker import NotificationWorker
from app.workers.outbox_worker import OutboxWorker
from app.workers.payment_worker import PaymentWorker


async def run_forever() -> None:
    configure_logging()
    await redis_runtime.connect()
    logger.info("workers.started")
    try:
        tick = 0
        next_backup_at = time.monotonic()
        while True:
            async with AsyncSessionLocal() as session:
                processed_payment = await PaymentWorker(session).process_next()
            async with AsyncSessionLocal() as session:
                processed_delivery = await FulfillmentService(session).process_next()
            async with AsyncSessionLocal() as session:
                processed_notification = await NotificationWorker(session).process_next()
            async with AsyncSessionLocal() as session:
                processed_outbox = await OutboxWorker(session).process_next()
            processed = {
                "payment": processed_payment,
                "fulfillment": processed_delivery,
                "notification": processed_notification,
                "outbox": processed_outbox,
            }
            now = time.time()
            for worker, did_process in processed.items():
                WORKER_HEARTBEAT.labels(worker).set(now)
                if did_process:
                    WORKER_JOBS.labels(worker, "processed").inc()
                await redis_runtime.heartbeat(worker)
            if tick % 60 == 0:
                async with AsyncSessionLocal() as session:
                    await AnalyticsWorker(session).aggregate_today()
                async with AsyncSessionLocal() as session:
                    await CleanupWorker(session).run()
            if settings.backup_enabled and time.monotonic() >= next_backup_at:
                await _run_scheduled_backup()
                next_backup_at = time.monotonic() + settings.backup_interval_hours * 3600
            tick += 1
            await asyncio.sleep(1 if processed_payment or processed_delivery or processed_notification or processed_outbox else 5)
    finally:
        await redis_runtime.close()


async def _run_scheduled_backup() -> None:
    lock_key = "ravenstore:locks:scheduled-backup"
    acquired = True
    if redis_runtime.client:
        acquired = bool(await redis_runtime.client.set(lock_key, "1", ex=3600, nx=True))
    if not acquired:
        return
    try:
        artifact = await BackupWorker().create_backup()
        logger.info(
            "backup.completed",
            path=artifact.path,
            size_bytes=artifact.size_bytes,
            checksum_sha256=artifact.checksum_sha256,
            encrypted=artifact.encrypted,
        )
    except Exception as exc:
        logger.exception("backup.failed", error_type=type(exc).__name__)
        WORKER_JOBS.labels("backup", "failed").inc()
    else:
        WORKER_JOBS.labels("backup", "processed").inc()


if __name__ == "__main__":
    asyncio.run(run_forever())
