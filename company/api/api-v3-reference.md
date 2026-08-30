---
title: Meridian API v3 Reference
category: api
author: Sam Whitfield
team: Product
created: 2025-05-20
updated: 2026-06-11
status: current
version: 3.4
---

# Meridian API v3 Reference

Meridian API **v3** is the current, GA API. It launched on 2025-05-20 and
supersedes v2 (`api/api-v2-reference.md`), which is deprecated and reaches
end-of-life on 2026-11-01. New customers are onboarded to v3 only.

- **Base URL:** `https://api.meridiandata.io/v3`
- **Content type:** `application/json; charset=utf-8`
- **Timestamps:** ISO-8601, always UTC, always with the `Z` suffix
  (e.g. `2026-06-11T14:03:22.481Z`).
- **IDs:** all resource identifiers are UUIDv7 strings.

## Authentication

Two mechanisms — pick based on endpoint:

- **JWT (Bearer):** for all read/write endpoints in Portal-style traffic.
  Header: `Authorization: Bearer <jwt>`. Tokens are issued by Gatekeeper
  (see `api/api-authentication.md`).
- **Write key:** for ingest endpoints (`/events`, `/events:batch`).
  Header: `X-Meridian-Write-Key: mrdn_wk_...`. Write keys are scoped to
  a single workspace and can be rotated in the Portal admin area.

If both headers are supplied, the JWT takes precedence for non-ingest
routes; on ingest routes the write key is required.

## Pagination

Cursor-based. All list endpoints accept:

- `?cursor=<opaque>` — omit for the first page.
- `?limit=<n>` — default 100, max 500.

Responses include:

```json
{
  "data": [...],
  "next_cursor": "eyJvZmZzZXQiOjEwMH0",
  "has_more": true
}
```

Never parse the cursor. It is opaque and its format will change.

## Error envelope

All error responses use the same shape:

```json
{
  "error": {
    "code": "workspace_not_found",
    "message": "No workspace with id 018f...",
    "request_id": "req_01J1QW9E7Y5AXM"
  }
}
```

Log `request_id` when opening a support ticket — it's indexed in Datadog.

## Endpoints (selected)

### Events (ingest)

```
POST /v3/events
X-Meridian-Write-Key: mrdn_wk_...
Content-Type: application/json

{
  "workspace_id": "018f9d2c-...-...",
  "event_name": "order_placed",
  "event_ts": "2026-06-11T14:03:22.481Z",
  "user_id": "usr_7291",
  "properties": {
    "order_id": "ord_44812",
    "revenue_cents": 8990,
    "currency": "USD"
  }
}
```

Batch: `POST /v3/events:batch` accepts up to 500 events per call.

### Cohorts

```
GET  /v3/workspaces/{workspace_id}/cohorts
POST /v3/workspaces/{workspace_id}/cohorts
GET  /v3/workspaces/{workspace_id}/cohorts/{cohort_id}
POST /v3/workspaces/{workspace_id}/cohorts/{cohort_id}:evaluate
```

Cohort definitions are JSON-DSL; see the Cohorts guide (linked from the
Portal Learn tab).

### Reports

```
GET  /v3/workspaces/{workspace_id}/reports
POST /v3/workspaces/{workspace_id}/reports
GET  /v3/workspaces/{workspace_id}/reports/{report_id}
POST /v3/workspaces/{workspace_id}/reports/{report_id}:run
```

`:run` returns a `job_id`; poll `/v3/jobs/{job_id}` for status.

### Workspaces

```
GET  /v3/workspaces
GET  /v3/workspaces/{workspace_id}
POST /v3/workspaces/{workspace_id}/members
GET  /v3/workspaces/{workspace_id}/members
```

Note that `workspace_id` is required in the URL path for scoped
endpoints, and in the body for creation endpoints — it is never a header
in v3. This is one of the biggest changes from v2 (see
`api/api-migration-v2-to-v3.md`).

## Rate limits

See `api/api-rate-limiting.md`. Responses include `X-RateLimit-Remaining`
and `X-RateLimit-Reset` headers, and 429 responses include `Retry-After`.

## Related

- `api/api-authentication.md`
- `api/api-rate-limiting.md`
- `api/api-migration-v2-to-v3.md`
- `api/api-v2-reference.md` (deprecated)
