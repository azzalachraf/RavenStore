# RavenStore Security Standard

## Trust boundaries

The FastAPI service is the only trusted business-data boundary. The Admin Dashboard, Storefront,
and Telegram Bot are untrusted API clients and never receive database credentials, encryption
keys, payment-provider secrets, inventory plaintext, or privileged service credentials.

Authentication uses short-lived issuer/audience-bound JWT access tokens and rotating refresh
tokens. Refresh-token hashes, session IDs, device metadata, rotation history, and reuse detection
are stored server-side. Reuse revokes every active session for the affected account. New passwords
use Argon2; existing bcrypt hashes are upgraded after successful login. Administrative authorization
is resolved from the database on every request using Owner, Admin, Moderator, Support, and Customer
roles rather than trusting the JWT role claim.

## Controls

- Production CORS accepts explicit HTTPS origins only.
- Bearer authentication avoids ambient-cookie CSRF. Do not move tokens into cookies without adding
  a server-issued CSRF token and strict SameSite cookie policy.
- Trusted proxy CIDRs control whether forwarded client IP headers are accepted.
- Sensitive endpoints such as `/metrics` require a bearer token or source allowlist.
- Binance callbacks require a valid signature, a timestamp within five minutes, and a one-time nonce.
- API keys are hashed, expiring, revocable, and associated with an active user.
- Login protection combines account lockout with Redis-backed per-email and per-IP throttling.
- Validation errors omit submitted values. Unexpected errors return only a message key and request ID.
- PDF and ZIP uploads remain quarantined until signature validation and, when configured, ClamAV
  scanning succeed. A file marked `quarantined_unscanned` must never be promoted for delivery.
- Activity, security, and webhook histories are append-only through PostgreSQL triggers.
- Next.js surfaces emit CSP, HSTS, clickjacking, MIME-sniffing, referrer, and permissions headers.

## Secret handling

Store production values in Render/Vercel/Supabase secret managers. Never commit `.env` files.
Rotate JWT secrets, API pepper, payment credentials, Telegram tokens, webhook secrets, backup keys,
and database credentials on a documented schedule and immediately after suspected exposure.
Changing the API pepper invalidates API keys and stored token lookups, so coordinate that rotation.

Use separate keys for `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `ENCRYPTION_KEY`,
`API_KEY_PEPPER`, and `BACKUP_ENCRYPTION_KEY`. Grant each service only the variables it consumes.

## Incident response

1. Preserve request IDs, security events, provider logs, and immutable audit history.
2. Revoke compromised sessions, API keys, webhook credentials, and provider credentials.
3. Isolate affected worker/API replicas and block malicious source ranges at the edge.
4. Restore from the latest verified backup into an isolated database and validate integrity.
5. Reconcile payments, transactions, inventory reservations, and deliveries before reopening writes.
6. Document impact, timeline, root cause, recovery, and preventive actions.

Report vulnerabilities privately to the platform owner. Do not place credentials or customer data in
an issue tracker.
