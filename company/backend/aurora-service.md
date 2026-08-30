---
title: Aurora — Ingest HTTP API
category: backend
author: wen.liu@meridiandata.io
team: Ingest
created: 2023-04-02
updated: 2026-07-14
status: current
version: 3.4
---

# Aurora

Aurora is the public event ingestion HTTP endpoint. Everything a customer sends
to `https://ingest.meridiandata.io` lands here first. It authenticates the
write, applies rate limits, does the bare minimum of payload validation, and
publishes onto the `events.raw` Kafka topic. All heavier work (enrichment,
schema validation against Cartograph, ClickHouse writes) happens downstream in
Pulse.

Aurora is deliberately dumb. If Pulse is unhealthy, Aurora keeps accepting
writes as long as Kafka is up — that is the whole point of splitting them
(ADR-0022, March 2023).

## Runtime

- **Language:** Go 1.22
- **Router:** `github.com/go-chi/chi/v5`
- **Deployment:** EKS (us-west-2), 4-pod baseline, HPA to 40 on CPU + custom
  Kafka producer-latency metric.
- **Owner:** Ingest team (Wen Liu). Reports operationally into Platform on-call.

## Endpoints (v3)

| Method | Path                  | Purpose                          |
|--------|-----------------------|----------------------------------|
| POST   | `/v3/events`          | Single event                     |
| POST   | `/v3/events/batch`    | Up to 500 events per request     |
| POST   | `/v2/track`           | **Deprecated.** EOL 2026-11-01.  |
| GET    | `/healthz`            | Liveness (always 200)            |
| GET    | `/readyz`             | Readiness (checks Kafka + Redis) |

The `/v2/track` handler is a thin adapter that translates the legacy envelope
into the v3 shape and re-enters the v3 code path. It emits a `v2_write_total`
counter with `workspace_id` labels so we can watch the tail of v2 traffic.

```go
r := chi.NewRouter()
r.Use(middleware.RequestID, middleware.RealIP, ratelimit.PerWorkspace)
r.Post("/v3/events",        h.PostEvent)
r.Post("/v3/events/batch",  h.PostEventBatch)
r.Post("/v2/track",         h.PostV2Track) // deprecated adapter
```

Event payload:

```go
type Event struct {
    WorkspaceID string            `json:"workspace_id"` // required in body (v3)
    Type        string            `json:"type"`
    Timestamp   time.Time         `json:"timestamp"`    // ISO-8601, RFC3339
    UserID      string            `json:"user_id,omitempty"`
    AnonID      string            `json:"anon_id,omitempty"`
    Properties  map[string]any    `json:"properties"`
    Context     map[string]string `json:"context,omitempty"`
}
```

## Authentication

Every request must include `X-Meridian-Write-Key`. Aurora validates the key
against a Redis-cached copy of the Postgres table `write_keys` (columns:
`id`, `workspace_id`, `hashed_key`, `revoked_at`, `last_used_at`). Cache TTL
is 60 seconds; misses fall through to Postgres and populate the cache.

Errors:

| Code       | HTTP | Meaning                                       |
|------------|------|-----------------------------------------------|
| `AUR-4001` | 401  | Missing `X-Meridian-Write-Key` header         |
| `AUR-4002` | 401  | Key not found or revoked                      |
| `AUR-4003` | 403  | Key belongs to a workspace in `suspended` state |
| `AUR-4008` | 400  | Malformed JSON envelope                       |
| `AUR-4013` | 413  | Batch exceeds 500 events or 4 MB              |
| `AUR-4029` | 429  | Per-workspace rate limit exceeded             |
| `AUR-5031` | 503  | Kafka producer unhealthy (readyz fails first) |

Write keys are per-workspace, never per-user. Rotating a key requires the
Portal Settings page; there is no API for it yet.

## Rate limiting

10,000 requests per second per workspace, enforced by a Redis token-bucket
implemented in the shared `ratelimit` package. The bucket key is
`rl:aurora:{workspace_id}:{second}`. Growth-tier workspaces get 1,000 rps;
Scale gets 5,000; Enterprise gets 10,000 default with per-account overrides in
the `workspaces.rate_limits_json` column. Batch requests count as `ceil(N/10)`
tokens, not N — this is different from `/v3/queries` in Beacon.

## Kafka producer

Aurora publishes to `events.raw` using the franz-go client. Topic has 96
partitions; partition key is `workspace_id` so all of one customer's traffic
lands in a small set of partitions. The 2025-01-22 backlog incident
(INC-2025-01-22) was caused by exactly this design under a single very large
new customer — the rebalancing runbook now covers the mitigation.

Producer settings: `acks=all`, `linger=5ms`, `max.in.flight=5`, LZ4
compression. `producer_error_total` and `kafka_produce_latency_ms` are the two
SLO metrics.

## What Aurora does NOT do

- No schema validation. Bad event shapes are accepted and dead-lettered by
  Pulse (Cartograph rejects them there).
- No enrichment (no geoip, no UA parse).
- No writes to ClickHouse or Postgres event tables.
- No customer-facing responses beyond `{"accepted": N}`.

See also: `backend/pulse-service.md`, `backend/cartograph.md`,
`runbooks/kafka-partition-rebalance.md`, `adrs/0022-kafka-between-ingest-and-pulse.md`.
