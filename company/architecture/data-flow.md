---
title: Data Flow
category: architecture
author: Wen Liu
team: Ingest
created: 2023-08-19
updated: 2026-06-30
status: current
version: 3.4
---

# Data Flow

How a customer event moves from an SDK call to a chart in the Portal.
Companion to `system-overview.md` and `event-pipeline.md`.

## Write path: SDK → Portal

1. **SDK → Aurora (HTTPS).**
   The customer's SDK (JS, iOS, Android, or server-side Node/Python/Go)
   posts a batch to `https://events.meridiandata.io/v3/track`. TLS
   terminates at CloudFront, which forwards to the ingest ALB, which
   round-robins across Aurora pods.
   - Auth: workspace write key in `Authorization: Bearer <key>`.
     Gatekeeper is called out-of-band by Aurora to validate + cache.
   - Payload: gzip'd JSON, up to 1MB per request, up to 500 events per
     batch.

2. **Aurora → Cartograph (validate).**
   For each event, Aurora asks Cartograph "is this event name valid for
   this workspace, and do the properties match the declared schema?"
   Cartograph responses are cached in Aurora for 60s per (workspace, event).
   Invalid events go to `events.dlq` with a rejection reason.

3. **Aurora → Kafka `events.raw`.**
   Accepted events are published to Kafka topic `events.raw`
   (96 partitions). The ordering key is `workspace_id`. Aurora responds
   `202 Accepted` to the SDK once the produce ack lands.

4. **Pulse consumes `events.raw`.**
   Pulse worker pods each own a consumer group `pulse-enrich`. For each
   event:
   - Parse User-Agent (browser/os/device).
   - Geo-enrich from IP (MaxMind DB in-pod).
   - Resolve identity — if `user_id` is unknown but `anonymous_id` maps
     to an existing user, backfill.
   - Attach cohort tags (via a periodic pull from Postgres).
   - Emit the enriched event to `events.enriched` (96 partitions).

5. **Pulse batch writer → ClickHouse.**
   A second Pulse role, `pulse-writer`, consumes `events.enriched` and
   batches inserts to ClickHouse. Batch config: up to 50k rows or 2s,
   whichever first. Writes go to the `events_local` table on the
   sharded distributed table.

## Read path: Portal → ClickHouse

1. **Portal → Beacon (query).**
   The dashboard makes REST calls to
   `https://api.meridiandata.io/v3/reports/*`. Auth is a Gatekeeper JWT
   passed in an `Authorization` header (the same JWT that the httpOnly
   cookie holds; see `portal-architecture.md`).

2. **Beacon → Beacon-Aggregator (fast path).**
   For common report shapes (daily active workspaces, event counts by
   name, funnel with ≤5 steps), Beacon first asks Beacon-Aggregator.
   The aggregator serves from Redis if hot, from Postgres if warm, and
   returns a cache-miss signal otherwise.

3. **Beacon → ClickHouse (slow path).**
   Cache miss, or a report shape that doesn't fit the aggregator, goes
   straight to ClickHouse via the query builder. Query timeouts are
   30s at the ClickHouse side, 35s at Beacon (INC-2025-09-30: earlier
   there was no upstream timeout).

## Latency budgets

These are the SLOs the pipeline is built against. See
`runbooks/investigate-ingest-lag.md` when they slip.

| Hop | p50 | p99 |
|-----|-----|-----|
| SDK → Aurora response (`202`) | 40ms | 250ms |
| Aurora → `events.raw` produce | 5ms | 40ms |
| Pulse enrichment (per event) | 12ms | 120ms |
| Pulse → ClickHouse batch write | 200ms | 1.2s |
| **End-to-end: ingest → queryable** | **8s** | **45s** |
| Beacon cached read (aggregator hit) | 40ms | 300ms |
| Beacon cold read (ClickHouse) | 800ms | 6s |

The end-to-end p99 of 45s is the number customers are told in the
public docs. It's dominated by the batch-writer's flush interval plus
ClickHouse merge visibility.

## Failure modes (very short)

- **Aurora down** — CloudFront serves stale 5xx; SDKs retry with
  jitter. Ingest is at-least-once from the SDK's perspective.
- **Kafka partition skew** (INC-2025-01-22) — one workspace saturates
  a single partition. Mitigation now uses a compound partition key for
  hot workspaces; see `event-pipeline.md`.
- **ClickHouse degraded** — Pulse writer backs off and buffers; if the
  buffer fills, older events spill to S3 (`meridian-events-archive`)
  and are replayed via Atlas.
- **Aggregator cold** — Beacon falls through to ClickHouse; higher
  latency but correct.
