---
title: Meridian API v2 Reference (deprecated)
category: api
author: Sam Whitfield
team: Product
created: 2022-11-14
updated: 2026-05-22
status: deprecated
version: 2.11
---

# Meridian API v2 Reference (deprecated)

> **This API is deprecated.** Originally slated for end-of-life on
> **2026-05-20**, the sunset was extended to **2026-11-01** to give a
> handful of Enterprise customers additional migration runway. No further
> extensions are planned. See `meetings/2025-05-15-api-v3-launch-review.md`
> for the original EOL decision. A separate extension announcement
> covers the 2026-11-01 date.
>
> New integrations MUST use v3 (`api/api-v3-reference.md`). Migration
> guide: `api/api-migration-v2-to-v3.md`.

- **Base URL:** `https://api.meridiandata.io/v2`
- **Content type:** `application/json`
- **Timestamps:** unix seconds (integer).
- **IDs:** mostly UUIDv4 strings, with a few older integer IDs on legacy
  endpoints.

## Authentication

v2 uses a single header for both read and ingest traffic:

```
X-Auth-Token: <jwt>
```

The JWT is issued by Gatekeeper (called `identity-service` in some
mid-2022 v2 docs — same service, renamed in 2023). Ingest write keys are
also passed via `X-Auth-Token` in v2; v3 splits them into
`X-Meridian-Write-Key`.

There is a header, sent in the response, that Enterprise customers on the
extended sunset need to be aware of. It is not documented here — see the
current PRD for details.

## Pagination

Offset-based:

```
GET /v2/reports?offset=0&limit=50
```

- `offset` defaults to 0.
- `limit` defaults to 50, max 200.

Response includes a top-level `total` count. This becomes prohibitively
expensive on large lists — the switch to cursor pagination is one of the
core reasons for v3.

## Error format

Flat string:

```json
{ "error": "workspace not found" }
```

No `code`, no `request_id`. Support tickets have to correlate on
timestamps.

## Endpoints (selected)

### Track (ingest)

```
POST /v2/track
X-Auth-Token: <write_key>
X-Workspace-Id: 018f9d2c-...-...
Content-Type: application/json

{
  "event": "order_placed",
  "timestamp": 1749650602,
  "user_id": "usr_7291",
  "properties": { "order_id": "ord_44812", "revenue_cents": 8990 }
}
```

Note the endpoint is `/track` in v2 and `/events` in v3. Note also that
`workspace_id` (called `X-Workspace-Id`) is a header — this moves into
the body in v3.

### Reports

```
GET  /v2/reports?offset=0&limit=50
POST /v2/reports
POST /v2/reports/{id}/run
```

### Cohorts

```
GET  /v2/cohorts?offset=0&limit=50
POST /v2/cohorts
POST /v2/cohorts/{id}/evaluate
```

## Rate limits

v2 read API: **500 requests/minute per workspace** (v3 raised this to
1000/min). Ingest: same 10K req/s soft limit as v3 — the ingest limiter
is shared. See `api/api-rate-limiting.md`.

## Support timeline

- 2025-05-20 — v3 GA. v2 deprecated.
- 2026-05-20 — original EOL. Extended.
- 2026-11-01 — final EOL. After this date, v2 endpoints return
  `410 Gone`.

Customer Support (Lin Zhao's team) tracks which customers are still on
v2 and drives outreach.

## Related

- `api/api-v3-reference.md`
- `api/api-migration-v2-to-v3.md`
- `api/api-authentication.md`
