---
title: Migrating from API v2 to v3
category: api
author: Lin Zhao
team: Support
created: 2025-06-02
updated: 2026-06-15
status: current
version: 2.1
---

# Migrating from Meridian API v2 to v3

This guide is for customers still on Meridian API v2. The v2 API is
**deprecated** and will be turned off on **2026-11-01** (see
`api/api-v2-reference.md` for the sunset history). After that date, all
v2 endpoints return `410 Gone`.

If you get stuck: `support@meridiandata.io`. Include your workspace ID
and, if you have one, a `request_id` from a v3 error response.

## Summary of breaking changes

| Area | v2 | v3 |
|---|---|---|
| Base URL | `https://api.meridiandata.io/v2` | `https://api.meridiandata.io/v3` |
| Auth (read/write) | `X-Auth-Token: <jwt>` | `Authorization: Bearer <jwt>` |
| Auth (ingest) | `X-Auth-Token: <write_key>` | `X-Meridian-Write-Key: <write_key>` |
| Workspace ID (POST) | `X-Workspace-Id` header | `workspace_id` in body |
| Pagination | Offset (`?offset=&limit=`) | Cursor (`?cursor=&limit=`) |
| Timestamps | Unix seconds (integer) | ISO-8601 UTC with `Z` |
| Error format | `{"error": "message"}` | `{"error": {"code","message","request_id"}}` |
| Ingest endpoint | `POST /v2/track` | `POST /v3/events` |
| Batch ingest | `POST /v2/track/batch` | `POST /v3/events:batch` |
| Report run | `POST /v2/reports/{id}/run` | `POST /v3/reports/{id}:run` |
| Read rate limit | 500 req/min per workspace | 1000 req/min per workspace |

## Field-by-field: an ingest example

**v2:**

```
POST /v2/track
X-Auth-Token: mrdn_wk_...
X-Workspace-Id: 018f9d2c-...-...

{
  "event": "order_placed",
  "timestamp": 1749650602,
  "user_id": "usr_7291",
  "properties": { "revenue_cents": 8990 }
}
```

**v3:**

```
POST /v3/events
X-Meridian-Write-Key: mrdn_wk_...

{
  "workspace_id": "018f9d2c-...-...",
  "event_name": "order_placed",
  "event_ts": "2026-06-11T14:03:22Z",
  "user_id": "usr_7291",
  "properties": { "revenue_cents": 8990 }
}
```

Note the field renames: `event` → `event_name`, `timestamp` →
`event_ts`. This is intentional — the v3 names are consistent across
every endpoint.

## Handling errors

The v2 flat string error will not survive migration verbatim in your
error-handling code. Update your handler to look at
`error.code` (a stable machine-readable string) and use `error.message`
only for logging. Always log `error.request_id` — it lets Support jump
straight to the right entry in Datadog.

## Migration script

We publish a codemod-style helper as an npm package:

```
npm install --save-dev @meridian/v2-v3-migrator
npx meridian-v2-v3-migrator ./src
```

It rewrites URL bases, header names, pagination loops, and the ingest
event field names in TypeScript/JavaScript codebases. It does NOT touch
your error-handling logic — that has to be a human review, because the
shape of the error object changed.

For Python and Go codebases, the migration is manual. Reference
implementations for both live in the `meridian-examples` GitHub repo.

## Cutover checklist

1. Read `api/api-v3-reference.md` end-to-end.
2. Pull `@meridian/v2-v3-migrator` (or the manual guide for your
   language) and run it in a branch.
3. Update error handling to read `error.code`.
4. Re-verify pagination — offset loops with a `total` field must be
   rewritten as cursor loops with `has_more`.
5. Test against staging (`https://api-staging.meridiandata.io/v3`).
6. Cut over production traffic.
7. Once all traffic is on v3, delete v2-only code paths.

## Related

- `api/api-v3-reference.md`
- `api/api-v2-reference.md`
- `api/api-authentication.md`
- `api/api-rate-limiting.md`
