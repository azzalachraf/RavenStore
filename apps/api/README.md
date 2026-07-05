# RavenStore API

Production backend for RavenStore. This service is the only source of truth for products,
orders, payments, fulfillment, analytics, users, localization, support, and admin operations.

Telegram bot and web clients must consume the REST API only. They must not store products or
business rules.

## Local development

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Deployable processes

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m app.workers.runner
```

Run at least two worker replicas in production. Payment, delivery, notification, and outbox
jobs are claimed with PostgreSQL row leases and `SKIP LOCKED`, so replicas can process the same
queues without duplicate work. API-generated delivery providers also receive the order item ID
as their idempotency key.

## Payment automation

Supported methods are `usdt_trc20`, `usdt_bep20`, and `binance`. Checkout configuration is read
from Admin-managed settings first and environment variables only provide bootstrap defaults:

- `payments.methods.usdt_trc20`
- `payments.methods.usdt_bep20`
- `payments.methods.binance`
- `payments.providers.binance` (store with `is_secret=true`)
- `automation.payment`
- `delivery.providers.<provider_key>`

Secret settings sent to `PUT /api/v1/settings/{key}` with `is_secret=true` are encrypted before
storage. Provider endpoints must use HTTPS. The API never returns encrypted payment references,
inventory payloads, provider credentials, or raw delivery payloads through admin list endpoints.

The customer flow is shared by every client:

1. Create an order at `POST /api/v1/orders`.
2. Create its payment at `POST /api/v1/payments/request`.
3. Submit a transaction hash or Binance order ID at `POST /api/v1/payments/verify`.
4. Poll payment/order state or consume website and Telegram notifications.
5. Read completed delivery through `GET /api/v1/orders/{order_id}/deliveries`.

Binance Pay sends signed callbacks to `POST /api/v1/webhooks/binance-pay`. Verification never
trusts a customer reference or webhook alone: the worker queries the provider, validates exact
amount, token contract, destination, receipt status, and configured confirmation count. Duplicate
references are serialized with an advisory lock and rejected across orders.

## Inventory and recovery

Admins create inventory pools and upload encrypted assets through the `/api/v1/admin/inventory`
endpoints. Finite inventory is reserved during checkout, committed after payment, and marked
delivered only when fulfillment succeeds. Expired checkouts release reservations automatically.
Accounts, credentials, invite links, license keys, and activation codes use inventory assets;
ZIP/PDF products use `product_downloads`; API-generated products use a configured delivery
provider. Unknown delivery types fail closed.

Provider failures use bounded exponential retries with jitter. Exhausted payments and deliveries
move to manual review, while stale worker leases are reclaimed by cleanup. Admin approval and
rejection endpoints are RBAC protected and audited. Payment attempts, transactions, invoices,
receipts, delivery logs, fraud signals, analytics events, notifications, and webhook payload hashes
provide the operational audit trail.

## Architectural rules

- API owns all business data.
- Telegram and website are API clients only.
- All user-facing text is resolved through translation keys.
- Payments are idempotent and auditable.
- Fulfillment is asynchronous and logged.
- Admin mutations emit activity logs and update timestamps.

## Real-time synchronization

Every mutation appends a versioned domain event to PostgreSQL in the same transaction. Workers
invalidate tagged Redis caches, publish the event to a retained Redis Stream, create idempotent
website/Telegram notifications, and record delivery latency. Browsers consume
`GET /api/v1/events/stream`; the Telegram bot consumes only public catalog, inventory,
localization, and settings topics and always refetches business data from REST.

Production requires `REDIS_URL`. See [docs/events.md](docs/events.md) for event contracts,
consumer authorization, scaling, monitoring, dead-letter recovery, and deployment checks.

Production security, monitoring, backup, restore, scaling, and test procedures are documented in
the repository-level `SECURITY.md`, `OPERATIONS.md`, and `TESTING.md` runbooks.
