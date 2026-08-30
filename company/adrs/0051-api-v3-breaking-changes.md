---
title: "ADR-0051: API v3 breaking changes and v2 deprecation timeline"
category: adr
author: Elena Vasquez
team: Product Eng
created: 2025-04-08
updated: 2025-05-12
status: Accepted
version: 1.0
---

# ADR-0051: API v3 breaking changes and v2 deprecation timeline

## Context

Our public API v2 has accumulated inconsistencies over four years:

- Mixed timestamp formats (unix seconds in some responses, ISO-8601 in
  others).
- Offset-based pagination that doesn't hold up on large `workspace_id`
  scans in ClickHouse.
- Flat error strings that don't carry a `request_id` for support tickets.
- `workspace_id` passed via `X-Workspace-Id` header, awkward for M2M
  clients using SDK auto-generated from OpenAPI.
- Some route names inherited from the Django monolith days
  (`/track` for event ingestion) don't match customer mental model.

We can't clean this up in-place without breaking every customer. A `v3`
gives us one paid moment of change.

## Decision

Introduce **API v3** at `https://api.meridiandata.io/v3` alongside v2.
v3 breaking changes:

1. **Cursor pagination** (`?cursor=<opaque>&limit=<n>`, max limit 500).
   Offset-based endpoints removed.
2. **ISO-8601 UTC timestamps everywhere.** No more unix seconds.
3. **Structured error envelope:**
   ```json
   { "error": { "code": "AUR-4001", "message": "...", "request_id": "..." } }
   ```
4. **`workspace_id` in request body**, not header, for all POST/PATCH.
   Read endpoints keep it in the URL path.
5. **Route renames:** `/track` → `/events`, `/track/batch` → `/events/batch`,
   `/reports/query` → `/queries`.
6. **New required header:** `X-Meridian-Api-Version: 3` on all requests
   (redundant with the URL, but makes SDK behavior explicit).

Auth model is unchanged (Bearer JWT or write-key).

**v2 deprecation timeline (as adopted 2025-05):**

| Date | Milestone |
|------|-----------|
| 2025-05-20 | v3 GA. |
| 2025-08 | v2 marked deprecated in docs; deprecation header on all v2 responses. |
| 2026-02 | Support tickets on v2 issues get "please upgrade" auto-reply. |
| 2026-05-20 | v2 EOL (original date). |

## Alternatives considered

- **Versionless evolution.** Keep patching v2. Rejected — the four items
  above can't be done without breaking clients.
- **v2.1 that reforms only errors and pagination.** Rejected — half
  measures leave the migration cost.
- **Fully backwards-compatible v3.** Rejected — the point is to fix the
  inconsistencies.

## Consequences

- Customer migration burden. We publish `@meridian/v2-v3-migrator` and
  the doc `api/api-migration-v2-to-v3.md`. Enterprise customers get
  hands-on help from Support.
- The v2 → v3 SDK release ships alongside v3 GA.
- Ledger and internal services must be migrated first (dogfood).

## Status

Accepted 2025-05-12. GA on 2025-05-20 as planned.

**Note (2026-05):** v2 EOL has been extended (see
`meetings/2025-05-15-api-v3-launch-review.md` and later comms) to
**2026-11-01** because too many enterprise workspaces had not migrated.
This ADR is not amended for the extension; check `api/api-v2-reference.md`
for the current EOL date.
