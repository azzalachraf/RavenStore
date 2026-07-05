# RavenStore Production Deployment

## Supabase

1. Rotate all credentials that have left the Supabase dashboard.
2. Add GitHub secrets `SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF`, and `SUPABASE_DB_PASSWORD`.
3. Run the `Supabase Storage Deployment` workflow once. It creates private `product-files` and
   `backups` buckets plus the public `product-images` bucket.
4. Copy the Session pooler connection string into Render as `DATABASE_URL` using the
   `postgresql+asyncpg://` scheme.
5. Enable Supabase point-in-time recovery when the selected plan supports it.

The service-role key exists only in Render's backend environment group. The Admin Dashboard and
Storefront never receive Supabase keys and never call Storage or PostgreSQL directly.

## Render

Before applying `render.yaml`, create three private Render environment groups:

### `ravenstore-backend-secrets`

Populate every backend variable from `apps/api/.env.example`. Generate distinct JWT access/refresh
secrets, Fernet encryption/backup keys, API pepper, and metrics token. Set `DATABASE_URL` to the
Supabase Session pooler URL and set the Supabase project URL, anon key, service-role key, bucket names,
Telegram bot token/username, receiver addresses, and provider credentials.

For the first deployment only, set `INITIAL_OWNER_EMAIL` and a unique 16+ character
`INITIAL_OWNER_PASSWORD`. Remove both variables after `python -m app.seed` creates the Owner account.

Keep `PAYMENT_TRC20_ENABLED`, `PAYMENT_BEP20_ENABLED`, and `PAYMENT_BINANCE_ENABLED` false until all
verification credentials for that provider are present. A Binance UID alone cannot verify Binance Pay
orders; merchant API credentials and the webhook public key are required for full automation.

### `ravenstore-bot-secrets`

Set `BOT_TOKEN`, `BOT_PUBLIC_USERNAME`, `WEBHOOK_BASE_URL`, `WEBHOOK_SECRET`, and `API_BASE_URL`.
`WEBHOOK_BASE_URL` is the bot Render HTTPS origin. `API_BASE_URL` is the API HTTPS origin with
`/api/v1` appended.

### `ravenstore-telegram-bridge`

Set `TELEGRAM_SERVICE_API_KEY` and `TELEGRAM_ADMIN_ID`. Use the same cryptographically random service
key for the API, worker, and bot. The numeric admin ID is not the bot username or Binance UID.

Create a Blueprint from `render.yaml`. It provisions persistent Redis plus API, worker, and bot
services in Frankfurt. Render runs Alembic and seed data before API deployment, waits on readiness
health checks, and deploys only after GitHub checks pass.

## Vercel

Import the repository twice as separate Vercel projects:

1. Admin project root: `apps/web`
2. Storefront project root: `apps/storefront`

Admin production variables:

- `NEXT_PUBLIC_API_BASE_URL=https://YOUR_API_DOMAIN/api/v1`
- `NEXT_PUBLIC_ADMIN_SITE_URL=https://YOUR_ADMIN_DOMAIN`

Storefront production variables:

- `NEXT_PUBLIC_API_BASE_URL=https://YOUR_API_DOMAIN/api/v1`
- `NEXT_PUBLIC_TELEGRAM_BOT_URL=https://t.me/YOUR_BOT_USERNAME`
- `NEXT_PUBLIC_SITE_URL=https://YOUR_STOREFRONT_DOMAIN`
- `RAVENSTORE_IMAGE_HOST=YOUR_PROJECT_REF.supabase.co`

Do not add the Supabase service-role key, database URL, Telegram token, Binance credentials, JWT keys,
or encryption keys to Vercel. Both Next.js projects fail production builds when required public URLs
are absent.

## GitHub and automatic deployment

Protect `main` and require the `RavenStore Production Gate` checks. Render's
`autoDeployTrigger: checksPass` deploys containers after those checks. Vercel's Git integration deploys
each configured monorepo root after a successful push. The Supabase workflow applies Storage changes,
and the production smoke workflow checks API, bot, Admin, and Storefront URLs.

Add these GitHub secrets for smoke checks:

- `PRODUCTION_API_URL`
- `PRODUCTION_BOT_URL`
- `PRODUCTION_ADMIN_URL`
- `PRODUCTION_STOREFRONT_URL`

Deployment credentials remain provider-managed and are never committed.
