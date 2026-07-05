# RavenStore Production Checklist

## Credentials

- [ ] Previously shared Telegram token revoked and replaced
- [ ] Previously shared Supabase service-role key rotated
- [ ] Previously shared database password reset
- [ ] Numeric Telegram Admin ID configured
- [ ] Initial Owner account created and bootstrap password variables removed
- [ ] RavenStore access and refresh JWT secrets are distinct
- [ ] Encryption, API pepper, backup, metrics, webhook, and service keys generated independently
- [ ] No `.env`, `.env.local`, private key, dump, or credential file is tracked by Git

## Supabase

- [ ] Session pooler connection tested from Render region
- [ ] Direct/session migration connection tested with `alembic current`
- [ ] Alembic upgraded through `202607050001`
- [ ] `product-files` and `backups` buckets are private
- [ ] `product-images` bucket is public-read and backend-write only
- [ ] Service-role key exists only on API/worker services
- [ ] Backup upload and isolated restore tested

## Payments

- [ ] TRC20 address, official contract, TronGrid key, and confirmations configured before enabling
- [ ] BEP20 address, official contract, explorer key, and confirmations configured before enabling
- [ ] Binance merchant API credentials and webhook public key configured before enabling
- [ ] Exact-amount, duplicate-reference, timeout, retry, fraud, and fulfillment tests pass in staging
- [ ] A low-value real transaction is reconciled end to end before launch

## Telegram

- [ ] Bot token, username, admin ID, service key, and webhook secret configured
- [ ] Telegram webhook points to the Render bot URL and reports no delivery errors
- [ ] `/start` creates an API-owned Telegram user and returns English/Arabic selection
- [ ] Catalog, checkout, payment verification, delivery, notifications, support, and referrals verified
- [ ] Bot never accesses PostgreSQL or Supabase directly

## Render and Vercel

- [ ] Render environment groups created before Blueprint sync
- [ ] API `/health/live` and `/health/ready` return success
- [ ] Bot `/health/live` and `/health/ready` return success
- [ ] Worker heartbeats are healthy and all queues are empty
- [ ] Admin and Storefront Vercel root directories and public variables configured
- [ ] CORS contains only production Admin and Storefront HTTPS origins
- [ ] CSP contains the production API and Supabase image host
- [ ] Custom domains and TLS certificates are active

## Release gates

- [ ] API Ruff, tests, migration, and dependency audit pass
- [ ] Telegram Ruff and tests pass
- [ ] Admin and Storefront typechecks, builds, and npm audits pass
- [ ] GitHub branch protection requires CI before deployment
- [ ] Supabase Storage deployment workflow succeeds
- [ ] Production smoke workflow succeeds
- [ ] Monitoring, alerts, logs, traces, and backup-failure notifications are connected
- [ ] Disaster recovery restore drill completed and recorded

RavenStore is production-ready only when every required item above is checked. Missing provider keys
must keep the corresponding payment method disabled; startup validation prevents a partially configured
method from becoming available.
