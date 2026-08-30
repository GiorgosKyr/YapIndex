---
title: Redis Usage at Meridian
category: database
author: Priya Ramanathan
team: Platform
created: 2023-11-02
updated: 2026-04-11
status: current
version: 2.2
---

# Redis Usage

Meridian runs three separate ElastiCache Redis 7 clusters. They are kept
distinct on purpose — mixing session state, rate-limiting counters, and
general cache in a single cluster made incident triage painful during 2022
and 2023, and made blast radius unpredictable. Each cluster has its own
maintenance window, sizing, and access policy.

None of these clusters are the source of truth for anything customer-facing.
See ADR-0044 and the "What Redis is NOT used for" section below.

## Clusters

### `meridian-cache-prod`

- **Purpose:** general-purpose cache. Beacon uses it for query result
  caching (see `backend/beacon-caching.md`), Portal uses it for user
  profile lookups, Cartograph uses it for schema-lookup memoization.
- **Sizing:** 3-node cluster, `cache.r7g.xlarge`, cluster mode enabled.
- **Eviction policy:** `allkeys-lru`.
- **TTLs:** callers must set explicit TTLs. Defaults enforced in
  `meridian-cache` shared library (60s for query results, 5 min for
  profile lookups).

### `meridian-ratelimit-prod`

- **Purpose:** rate limiting for Aurora (ingest) and Beacon (read API).
  Token bucket state per (workspace, endpoint class). See
  `api/api-rate-limiting.md` for the limits themselves.
- **Sizing:** 2-node cluster, `cache.r7g.large`.
- **Eviction policy:** `allkeys-lru` — expired buckets are cheap to
  reconstruct, and losing a bucket briefly just means the customer gets a
  fractional grace period.
- **Access:** only Aurora and Beacon speak to this cluster. Enforced by
  security group.

### `meridian-sessions-prod`

- **Purpose:** Gatekeeper session store. Portal cookies and API refresh
  tokens are dereferenced against this. Not the JWT revocation list — that
  lives in DynamoDB (see `database/dynamodb-usage.md`).
- **Sizing:** 3-node cluster, `cache.r7g.large`, cluster mode enabled.
- **Eviction policy:** `allkeys-lru`. Session records also have a hard TTL
  matching the access token expiry (60 min) plus a small grace.
- **Persistence:** AOF disabled. Losing this cluster forces a re-login for
  active users; it does not lose customer data. This is a deliberate
  trade-off.

## What Redis is NOT used for (any more)

- **NOT usage counters.** MTE counters live in Postgres
  (`usage_counters` table) since 2025-03-19. The reason is INC-2025-03-08 —
  Redis eviction under memory pressure caused a counter reset which
  re-billed customers on the next Ledger tick. ADR-0044 forbids Redis as
  the source of truth for anything the business cares about.
- **NOT the JWT revocation list.** That's DynamoDB
  (`gatekeeper-revoked-jwt-ids`) because we want the durability guarantees.
- **NOT a queue.** Kafka handles event streaming and SQS handles async
  jobs. Redis Streams is used for a couple of small internal fanouts
  inside single services but is not a shared queue.

## Access

Redis auth is via IAM (ElastiCache RBAC). No static AUTH tokens. Password
rotation is therefore N/A — see `security/secrets-rotation.md`.

## Related

- ADR-0044 — usage counters source of truth
- `database/postgres-schema.md` — `usage_counters` table
- `api/api-rate-limiting.md`
- `security/authentication.md`
