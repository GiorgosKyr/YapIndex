---
title: Pulse — Stream Processor
category: backend
author: wen.liu@meridiandata.io
team: Ingest
created: 2023-04-10
updated: 2026-06-22
status: current
version: 2.9
---

# Pulse

Pulse is the Kafka consumer that turns raw ingested events into enriched,
schema-validated rows in ClickHouse. It's the second half of the ingest path;
Aurora produces onto `events.raw`, Pulse consumes and does the real work.

Pulse existed as a design goal in the original 2019 monolith but was only
extracted in March 2023 when Kafka was introduced (ADR-0022). Before that,
Aurora wrote directly to ClickHouse, which coupled ingest availability to the
analytics cluster.

## Runtime

- **Language:** Go 1.22
- **Deployment:** EKS (us-west-2), 12-pod baseline, HPA to 60 on consumer lag.
- **Owner:** Ingest team (Wen Liu).
- **Topics consumed:** `events.raw` (96 partitions, consumer group
  `pulse-enricher`).
- **Topics produced:** `events.enriched` (fanout for internal consumers like
  Lighthouse), `events.dlq` (schema failures).

## Pipeline

Each pod runs N goroutines, one per assigned partition. The steps for each
message are:

1. **Deserialize** the envelope from JSON.
2. **Enrich**:
   - GeoIP from client IP via MaxMind GeoLite2-City DB (mmap'd on pod start,
     refreshed weekly by the sidecar `mmdb-updater`).
   - User-agent parse via `github.com/ua-parser/uap-go`. We keep browser
     family, OS family, and device type.
   - Server-side timestamp (`ingested_at`) already stamped by Aurora — Pulse
     just carries it through.
3. **Validate** against the workspace's schema for `event.type`. This is a
   gRPC call to Cartograph (`ValidateEvent`, 50ms timeout, hedged after 20ms
   to a second Cartograph replica).
4. **Batch** into ClickHouse writes. Target: 50,000 rows or 5 seconds,
   whichever comes first.
5. **Ack** to Kafka only after the ClickHouse batch commits.

Pseudocode of the batch loop:

```go
for {
    select {
    case msg := <-partitionCh:
        row, err := enrichAndValidate(msg)
        if err != nil {
            dlq.Produce(msg, err)   // events.dlq
            continue
        }
        batch = append(batch, row)
        if len(batch) >= 50_000 { flush() }
    case <-time.After(5 * time.Second):
        if len(batch) > 0 { flush() }
    }
}
```

## ClickHouse writes

Rows land in `events` (the wide fact table) — one row per event, `Distributed`
engine over `events_local` on each of the 6 shards. Batch inserts use the
native protocol via `github.com/ClickHouse/clickhouse-go/v2`. On write
failure Pulse retries the whole batch 3x with exponential backoff (500ms,
2s, 8s); if all three fail the batch is written to S3
(`meridian-events-archive/pulse-failed/`) and the batch offsets are still
committed. A daily replay job in Atlas picks up the S3 files. This is the
mitigation we adopted after INC-2025-01-22, when a ClickHouse blip caused
Pulse to stall the whole partition group.

## Dead-letter behavior

Any message rejected in step 3 goes to `events.dlq` with headers:

- `x-mrdn-reject-reason`: e.g. `SCHEMA_UNKNOWN_TYPE`, `SCHEMA_TYPE_MISMATCH`,
  `SCHEMA_MISSING_REQUIRED`
- `x-mrdn-workspace-id`
- `x-mrdn-original-topic`: `events.raw`

Error codes surfaced to internal tooling:

| Code       | Meaning                                       |
|------------|-----------------------------------------------|
| `PLS-4101` | Unknown event type for workspace              |
| `PLS-4102` | Required property missing                     |
| `PLS-4103` | Property type mismatch                        |
| `PLS-5210` | Cartograph unreachable (batch retried)        |
| `PLS-5220` | ClickHouse write failed after 3 retries       |

The Portal shows a "rejected events" chart in Settings → Data Quality that
reads a Beacon-aggregated view over `events.dlq` counters.

## Observability

Prometheus metrics exposed on `:9102/metrics`:

- `pulse_consumer_lag_records{topic,partition}`
- `pulse_enrich_duration_ms` (histogram, geoip + UA + validate)
- `pulse_clickhouse_batch_size` (histogram)
- `pulse_clickhouse_flush_duration_ms`
- `pulse_dlq_produced_total{reason}`

Datadog scrapes these; SLO alerts fire on `consumer_lag_records > 500_000
for 5 min` or `dlq_produced_total` rate > 1% of consumed rate.

See also: `backend/aurora-service.md`, `backend/cartograph.md`,
`runbooks/kafka-partition-rebalance.md`.
