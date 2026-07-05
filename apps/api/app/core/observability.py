from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

HTTP_REQUESTS = Counter("ravenstore_http_requests_total", "HTTP requests processed", ("method", "route", "status"))
HTTP_LATENCY = Histogram(
    "ravenstore_http_request_duration_seconds",
    "HTTP request latency",
    ("method", "route"),
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
WORKER_HEARTBEAT = Gauge("ravenstore_worker_last_heartbeat_timestamp", "Last worker heartbeat", ("worker",))
WORKER_JOBS = Counter("ravenstore_worker_jobs_total", "Worker jobs processed", ("worker", "outcome"))
PAYMENT_VERIFICATIONS = Counter("ravenstore_payment_verifications_total", "Payment verification outcomes", ("outcome",))
FULFILLMENTS = Counter("ravenstore_fulfillments_total", "Fulfillment outcomes", ("outcome",))
OUTBOX_EVENTS = Counter("ravenstore_outbox_events_total", "Outbox event outcomes", ("outcome",))


def observe_http(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS.labels(method, route, str(status_code)).inc()
    HTTP_LATENCY.labels(method, route).observe(duration_seconds)


def prometheus_payload() -> bytes:
    return generate_latest()
