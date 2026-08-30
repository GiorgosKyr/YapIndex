---
title: API FAQ
category: support
author: Lin Zhao
team: Support
created: 2024-05-18
updated: 2026-07-01
status: current
version: 5.2
---

# API FAQ

## Which API version should I use?

**v3** (`https://api.meridiandata.io/v3`). It has been GA since
2025-05-20 and is where all new features land.

**v2** is deprecated but still supported until **2026-11-01**. If you're
starting a new integration, use v3. Migration guide:
[api/api-migration-v2-to-v3.md](../api/api-migration-v2-to-v3.md).

## How do I authenticate?

Two options depending on the endpoint:

- **Ingest endpoints** (`POST /v3/events`, `POST /v3/events/batch`) —
  use a **write key** in the `X-Meridian-Write-Key` header. Generate
  write keys in Portal → Settings → API Keys.
- **All other endpoints** — use a **JWT bearer token** in the
  `Authorization: Bearer <token>` header. Get tokens via the OAuth
  client-credentials flow at `POST /v3/oauth/token`.

Full reference: [api/api-authentication.md](../api/api-authentication.md).

## I'm getting `401 Unauthorized`. What do I do?

Check in this order:
1. Are you using the right auth mechanism for the endpoint (write key vs
   JWT)? Ingest endpoints do NOT accept bearer tokens.
2. Has your JWT expired? Access tokens are valid for 60 minutes.
3. Is your write key active? Deactivated keys return 401.
4. If you were affected by the **2024-08 auth token rotation** (all
   sessions were invalidated), you need to re-issue any long-lived
   tokens from that period.

## Why am I getting 429s?

You're hitting a rate limit. Defaults:
- Ingest: 10K requests/second per workspace (soft), 20K burst.
- Read API (v3): 1000 requests/minute per workspace.
- Read API (v2): 500 requests/minute per workspace.

429 responses include a `Retry-After` header in seconds. Back off and
retry.

If you need higher limits, contact support with a description of your
use case. Enterprise workspaces can request custom limits.

Details: [api/api-rate-limiting.md](../api/api-rate-limiting.md).

## Why don't I see events I just sent?

There's a small ingest → queryable delay. Budgets:
- p50: ~8 seconds
- p99: ~45 seconds

Under normal conditions events show up in dashboards within 10 seconds.
If you're waiting significantly longer, check:
- Our status page: [status.meridiandata.io](https://status.meridiandata.io)
- The dead-letter reason on the event (schema validation failure will
  put the event in DLQ; see the `Events → Debug` tab in Portal).

Historically there have been ingestion delays during high-load events —
see [INC-2025-01-22](../incidents/INC-2025-01-22-aurora-backlog.md) for
one example.

## What's the difference between an event and a metric?

- **Event:** a single occurrence — one purchase, one page view, one
  click. Sent via the ingest API. Also called a "data point" in older
  docs.
- **Metric:** an aggregation over events — "purchases this week",
  "revenue per user", "conversion rate". Computed by Beacon.

## How do I test my integration without hitting production usage limits?

Use a sandbox workspace. Create one in Portal → Workspaces → Create
sandbox. Sandbox workspaces don't count toward your billable MTEs.

## Where can I get the OpenAPI spec?

`https://api.meridiandata.io/v3/openapi.json`. The Portal API Reference
page also embeds it with a live "Try it" widget.

## Which region are API calls served from?

All API calls are served from `us-west-2` today. EU customers with data
residency requirements can pre-register for the Frankfurt region rollout
(Q4 2026 target). See [product/prd-eu-region.md](../product/prd-eu-region.md)
for scope.

## More help

- Docs: [docs.meridiandata.io](https://docs.meridiandata.io)
- Support: `support@meridiandata.io`
- Enterprise: Slack Connect channel (ask your CSM)
