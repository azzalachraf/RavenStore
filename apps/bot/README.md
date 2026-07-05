# RavenStore Telegram Bot

Aiogram 3 Telegram client for RavenStore. The bot is the primary product surface, but it is
strictly a REST API client. It does not access PostgreSQL, Supabase, SQLAlchemy, or any backend
business logic directly.

## Run locally

```powershell
cd apps/bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
copy .env.example .env
python -m raven_bot.main
```

Use `BOT_MODE=polling` for local development. Production should use webhook mode.

## REST-only rule

Every product, category, order, payment, ticket, referral, wallet, profile, setting, notification,
and analytics action goes through `API_BASE_URL`.
The bot opens one authenticated SSE connection to the RavenStore API for catalog, inventory,
localization, and settings invalidations. It never consumes delivery or business payloads from the
event stream and never stores products. Every user interaction refetches current data from REST;
events only clear presentation caches and make the next render immediate.
