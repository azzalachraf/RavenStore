# RavenStore Event System

## Guarantees

- PostgreSQL remains the source of truth.
- State and its outbox event commit atomically.
- Redis Stream publication is at least once; `event_id` is the stable idempotency key.
- Events are ordered per aggregate by `partition_key`; consumers must not assume global ordering.
- Cache invalidation precedes publication, so a client refetch after receiving an event cannot read
  the previous Redis response cache generation.
- Failed deliveries retry with bounded exponential backoff and move to a durable dead-letter state.

## Envelope v1

Every stream item contains one JSON `event` field with:

```json
{
  "event_id": "uuid",
  "event_type": "product.price_changed",
  "topic": "catalog",
  "schema_version": 1,
  "aggregate_type": "product",
  "aggregate_id": "uuid",
  "partition_key": "product:uuid",
  "audience": "public",
  "occurred_at": "RFC3339 timestamp",
  "correlation_id": "request id",
  "causation_id": null,
  "trace_id": "request id",
  "cache_tags": ["products"],
  "payload": {"product_id": "uuid"}
}
```

Payloads contain identifiers, status, changed field names, and safe routing metadata only. Secrets,
credentials, delivery payloads, payment tokens, and encrypted values are never published.

## Audiences

- `public`: anonymous catalog/localization clients and authenticated clients.
- `customer`: the matching `payload.user_id` and authorized admin roles.
- `admin`: Owner, Admin, Moderator, and Support roles.
- `internal`: never exposed through SSE.

The SSE endpoint accepts `Authorization` or `X-API-Key`, an optional comma-separated `topics`
query, and `Last-Event-ID` for Redis Stream replay. Clients deduplicate by `event_id`.

## Cache Strategy

Public product, category, language, and translation GET responses use Redis response caching with
ETags. Cache keys include tag generations. Domain events increment affected generations instead of
performing key scans, which keeps invalidation constant time under horizontal scale. Browser clients
use `no-store` when refetching after an event. Polling remains a slow recovery fallback.

## Operations

Run multiple API and worker replicas against the same PostgreSQL and Redis services. Outbox jobs use
`FOR UPDATE SKIP LOCKED`; stale leases are reclaimed by cleanup. Redis Stream retention is controlled
by `EVENT_STREAM_MAX_LENGTH` and should exceed the longest expected client outage.

Monitor:

- `GET /health/ready` for PostgreSQL and Redis readiness.
- `GET /api/v1/events/health` for backlog, dead letters, failed deliveries, consumers, and transport metrics.
- `GET /api/v1/events/dead-letters` for operator inspection.
- `POST /api/v1/events/{event_id}/replay` after correcting the underlying failure.

Alert on a growing outbox backlog, any dead letter, Redis unavailability, stale consumers, sustained
delivery latency, or cache hit-rate collapse. `correlation_id` and `trace_id` connect API logs,
activity logs, outbox rows, and delivery records.

## Deployment Gate

1. Apply Alembic through `202607040002`.
2. Configure a durable Redis instance and `REDIS_URL` for API, worker, and bot processes.
3. Start at least two worker replicas.
4. Verify `/health/ready` returns 200.
5. Update a test product and confirm the event is processed, the cache generation advances, and
   storefront/admin/bot clients refetch without restart.
