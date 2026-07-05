# RavenStore Storefront

Secondary customer-facing web client for RavenStore. The storefront never stores products or
business rules. Catalog, localization, customer, order, payment, referral, notification and
support data are loaded from the FastAPI REST API.

## Local development

```powershell
cd apps/storefront
copy .env.example .env
npm install
npm run dev -- --port 3001
```

The Admin Dashboard remains a separate application in `apps/web` on port 3000.

## Verification

```powershell
npm run typecheck
npm run build
npm audit --audit-level=moderate
```

## Deployment

Deploy this directory as its own Vercel project. Set `NEXT_PUBLIC_API_BASE_URL`,
`NEXT_PUBLIC_TELEGRAM_BOT_URL`, and `NEXT_PUBLIC_SITE_URL` in the deployment environment.
Client views maintain one SSE connection to `/api/v1/events/stream`. Catalog, stock, translation,
order, payment, delivery, support, referral, and notification events trigger tagged REST
revalidation. Slow polling remains only as an outage recovery fallback.
