# RavenStore Admin Dashboard

The dashboard consumes the RavenStore REST API as its only source of truth. One authenticated SSE
connection receives versioned domain events and triggers tagged revalidation across dashboard
widgets. Product writes include `expected_updated_at` for optimistic concurrency; a conflicting
admin edit is rejected instead of silently overwriting newer state.

Event health, delivery failures, consumer status, and dead letters are available through the
`/api/v1/events` administration endpoints.
