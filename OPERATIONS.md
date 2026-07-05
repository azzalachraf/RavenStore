# RavenStore Production Operations

## Deployment topology

Run the API and worker as independent Render services from `apps/api/Dockerfile`. The API command is
the image default. The worker command is `python -m app.workers.runner`. Run Alembic once as a release
step before new application replicas receive traffic. Deploy the Admin Dashboard and Storefront as
separate Vercel projects. Deploy the Telegram Bot from `apps/bot/Dockerfile` in webhook mode.

Production requires Supabase PostgreSQL with SSL, Redis, persistent or object-backed storage for
backups/uploads, explicit HTTPS CORS origins, and different access/refresh JWT secrets. Start with at
least two API replicas and two worker replicas. PostgreSQL row locks and `SKIP LOCKED` make payment,
fulfillment, notification, and outbox workers horizontally safe.

## Release procedure

1. Run API Ruff, unit tests, integration tests, bot tests, both TypeScript checks, and both Next builds.
2. Back up PostgreSQL and verify the generated manifest/checksum.
3. Apply `alembic upgrade head` from one release process.
4. Deploy workers, API, Telegram Bot, Admin Dashboard, then Storefront.
5. Verify `/health/live`, `/health/ready`, `/metrics`, worker heartbeats, event backlog, and a synthetic
   catalog read. Complete a low-value payment in the provider sandbox before enabling production flow.
6. Roll back application images if probes or error budgets regress. Database downgrades require an
   explicit data-impact review; prefer a forward repair migration.

## Monitoring and alerts

Scrape `/metrics` using `METRICS_BEARER_TOKEN` or an allowlisted monitoring network. Export traces by
setting `OTEL_EXPORTER_OTLP_ENDPOINT`. JSON logs go to stdout and include request IDs, latency, status,
hashed client IP, event traces, worker outcomes, and failure types. Route stdout to the centralized
logging provider configured for Render.

Alert immediately on readiness failure, stale worker heartbeat, any dead-letter growth, invalid
webhook spikes, refresh-token reuse, critical security events, payment verification error rate,
fulfillment failures, backup failure, or sustained p95 API latency above 750 ms. Warn on outbox backlog
above 100, low inventory, cache hit-rate regression, database pool saturation, and disk usage above 75%.

The Admin `Security` screen refreshes every 15 seconds. `Health` covers event transport and queues.
Prometheus remains authoritative for historical alerts and SLO reporting.

## Backups and restore

The worker creates a PostgreSQL custom-format dump, verifies it with `pg_restore --list`, computes a
SHA-256 checksum, optionally encrypts it with Fernet, writes a manifest, and enforces retention.
Back up the persistent upload directory and Admin-managed configuration separately through the storage
provider. Keep one daily copy for 30 days and monthly copies in a second region/account.

Restore into an empty isolated database:

```bash
sha256sum ravenstore-YYYYMMDDHHMMSS.dump  # compare with checksum_sha256 in the JSON manifest
pg_restore --clean --if-exists --no-owner --dbname "$RESTORE_DATABASE_URL" ravenstore-YYYYMMDDHHMMSS.dump
alembic upgrade head
```

For encrypted artifacts, decrypt with the controlled backup key before `pg_restore`. Validate row
counts, recent orders, payment/transaction reconciliation, inventory totals, translation/settings
checksums, and outbox consistency. Point staging at the restored database before production cutover.
Target RPO is 24 hours from scheduled dumps plus Supabase point-in-time recovery when enabled. Target
RTO is four hours; test a full restore quarterly.

## Scaling and maintenance

- Scale API replicas on CPU, p95 latency, and connection utilization.
- Scale workers on oldest queued-job age and backlog, not CPU alone.
- Keep total SQLAlchemy pool capacity below the Supabase connection limit; use Supabase pooler endpoints.
- Add indexes only from measured slow-query plans. Use keyset pagination when admin datasets exceed the
  current bounded list endpoints.
- Vacuum/analyze PostgreSQL, review index bloat, rotate secrets, test restores, inspect dead letters,
  and review RBAC membership on a fixed maintenance schedule.

## Troubleshooting

- `503 /health/ready`: check PostgreSQL connectivity, Redis, SSL settings, pool exhaustion, and secrets.
- Stale workers: inspect worker logs, Redis heartbeat keys, database locks, provider timeouts, and circuit state.
- Payment backlog: inspect verification attempts, provider health, network confirmation thresholds, and fraud rules.
- Delivery backlog: inspect inventory reservations, provider configuration, encrypted payload availability, and dead letters.
- Synchronization lag: inspect outbox age, Redis Stream health, consumer checkpoints, and cache invalidations.
- Login lockouts: inspect immutable security events before unlocking or revoking sessions.
