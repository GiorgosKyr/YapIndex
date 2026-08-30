---
title: API Rate Limiting
category: api
author: Wen Liu
team: Ingest
created: 2024-03-14
updated: 2026-04-22
status: current
version: 3.0
---

# API Rate Limiting

Meridian applies rate limits at two layers: the public **ingest** API
(Aurora) and the public **read** API (Beacon). Both share the same
underlying limiter — a token bucket implemented in Redis
(`meridian-ratelimit-prod`, see `database/redis-usage.md`) — but the
policies differ.

All limits are per-workspace, not per-key or per-IP. This matches how
customers are billed and reason about capacity.

## Ingest limits

The ingest API is designed to be a firehose; the limits below exist to
protect the platform from a single workspace becoming a "hot" Kafka
partition (this is the failure mode from INC-2025-01-22).

- **Steady-state:** 10,000 requests/second per workspace (soft).
- **Burst:** 20,000 requests/second per workspace, absorbed by the token
  bucket's 60-second capacity.
- **Batch endpoint:** `POST /v3/events:batch` counts as one request but
  contributes N events to the workspace's MTE meter. The 500-events-per-batch
  cap is a separate limit.

The 10K/s figure is a **soft** limit — hitting it triggers Datadog
alerting to the account manager for a proactive conversation about tier
sizing, not an immediate 429. The **hard** limit at which 429s begin is
the 20K/s burst ceiling.

## Read API limits

Read API limits are stricter because read queries are more expensive
(they fan out to ClickHouse) and less bursty by nature.

- **v3:** 1000 requests/minute per workspace.
- **v2 (deprecated):** 500 requests/minute per workspace.

The v2 → v3 raise happened at the v3 GA (2025-05-20) and is one of the
carrots for migration (see `api/api-migration-v2-to-v3.md`).

## 429 responses

When a workspace exceeds a limit, the request is rejected with HTTP 429
and the standard error envelope:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 3
Content-Type: application/json

{
  "error": {
    "code": "rate_limited",
    "message": "Workspace has exceeded 1000 req/min on the read API.",
    "request_id": "req_01J1RCQ8X4NHF3"
  }
}
```

`Retry-After` is in seconds. Well-behaved clients should honour it and
back off; the ingest SDK does this automatically with jitter.

## Implementation

The limiter is a Lua script on `meridian-ratelimit-prod` implementing a
token bucket, keyed as `rl:{workspace_id}:{class}` where `class` is one
of `ingest`, `read_v3`, `read_v2`. Bucket state is ephemeral — losing
the Redis cluster briefly means customers get a fractional grace period,
which is intentional (see `database/redis-usage.md`).

Aurora and Beacon share the same shared library
(`meridian-ratelimit-client`) so behaviour is consistent across
languages (Go and Python).

## Excluded traffic

The following requests bypass rate limits and are counted separately:

- `GET /v3/healthz` and other health checks
- Portal-internal calls authenticated with the internal service JWT
- Beacon internal warm-cache jobs

## Related

- `api/api-authentication.md`
- `api/api-v3-reference.md`
- `database/redis-usage.md`
- Runbook: `runbooks/investigate-rate-limit-alerts.md`
