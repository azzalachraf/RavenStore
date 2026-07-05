# RavenStore Test Strategy

## Required suites

API unit tests cover token claims, password hashing, payment amount matching, webhook signatures,
delivery-provider rejection, event policies, retries, circuit breakers, and file quarantine. API
integration tests run against a migrated disposable PostgreSQL database and Redis. Bot tests verify
localization and that real-time events invalidate presentation state without storing catalog data.
Next.js projects require TypeScript checks and production builds.

Run locally:

```powershell
cd apps/api
python -m pytest -q
python -m ruff check app tests
pip-audit .

cd ../bot
python -m pytest -q
python -m ruff check raven_bot tests

cd ../web
npm run typecheck
npm run build

cd ../storefront
npm run typecheck
npm run build
```

CI must provision PostgreSQL and Redis, apply every Alembic migration, and set isolated test secrets.
Payment-provider calls, Telegram delivery, ClamAV, OTLP, and object storage use controlled test doubles.
Never run automated tests against production credentials or addresses.

## Release gates

A release fails on any test, migration failure, type error, production build error, critical dependency
advisory, leaked-secret finding, or high-severity static-analysis finding. End-to-end staging validates:

1. Register, login, refresh rotation, session revocation, and refresh reuse response.
2. Catalog read and Admin mutation propagating to Storefront and Telegram consumers.
3. Order creation, inventory reservation, payment verification, transaction creation, fulfillment,
   customer notification, invoice, receipt, and duplicate-payment rejection.
4. Failed provider retries, circuit opening, dead-letter transition, and recovery.
5. Signed/replayed webhook behavior and upload quarantine behavior.
6. Backup generation, checksum verification, restore, and post-restore reconciliation.

Load tests should model catalog browsing, authentication, checkout bursts, SSE clients, and Admin reads.
Track p50/p95/p99 latency, error rate, database connections, Redis latency, oldest queue age, and worker
throughput. Increase load gradually and stop before third-party provider rate limits are approached.
