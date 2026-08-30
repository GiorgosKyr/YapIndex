---
title: Event Pipeline (Aurora + Pulse + Kafka)
category: architecture
author: Wen Liu
team: Ingest
created: 2023-04-06
updated: 2026-05-27
status: current
version: 4.1
---

# Event Pipeline

Deep dive on the ingest side: **Aurora → Kafka → Pulse → ClickHouse**.
Companion to `data-flow.md` (which is the end-to-end path) and
`system-overview.md` (which is one level up).

## Aurora

- Go 1.22, `chi` router. Deployed to EKS `prod-uw2`, namespace
  `ingest`, HPA between 12 and 60 pods.
- Public endpoint: `https://events.meridiandata.io/v3/track`.
- Fronted by CloudFront (TLS + geo-based edge) → NLB
  (`nlb-ingest-prod`) → Aurora pods.
- Auth: workspace write key. Validated against Gatekeeper on first
  hit for a key, then cached for 5 min per pod.
- Schema check: Cartograph. 60s per (workspace, event) cache.
- Rate limits: 200 req/s per write key by default (customer-tunable
  on Scale and Enterprise), tokens in Redis.

Aurora acknowledges the SDK **only after** the Kafka produce ack for
`events.raw` lands. Producer config: `acks=all`, `min.insync.replicas=2`.

## Kafka (MSK)

Cluster: `msk-prod-uw2`, 12 broker nodes (`m5.large`), 3 AZs, IAM
auth on the internal listener. Version pinned in Terraform.

### Topic layout

| Topic | Partitions | Retention | Notes |
|-------|-----------|-----------|-------|
| `events.raw` | 96 | **3 days** | Aurora produces, Pulse (enrich) consumes |
| `events.enriched` | 96 | **7 days** | Pulse (enrich) produces, Pulse (writer) + Relay consume |
| `events.dlq` | 8 | 14 days | Rejected events with rejection reason header |

96 partitions on the two hot topics = 12 brokers × 8, giving even
partition ownership across the fleet with slack for broker loss.

### Ordering key

The ordering key for `events.raw` and `events.enriched` is
`workspace_id`. This keeps all events for one workspace on one
partition, which:

- Lets Pulse maintain per-workspace state (session stitching, cohort
  tag application) with no cross-partition coordination.
- Keeps event ordering stable *within a workspace*, which is what
  customers observe and reason about.

## Partition hot-spotting (and the mitigation)

### Background — INC-2025-01-22

On 2025-01-22 we onboarded a new Scale-tier customer whose peak
volume was ~4x our largest existing workspace's. Their entire event
stream landed on a single Kafka partition (because the key is
`workspace_id`). That partition's Pulse consumer fell behind by
~4 hours before we noticed and rebalanced.

Post-incident work: runbook `runbooks/rebalance-kafka-partitions.md`
plus the partitioning change below.

### Current partitioning strategy

For workspaces flagged as "high-volume" in the workspace metadata,
the produce-side key is:

```
key = workspace_id + ":" + fnv1a32(session_id) % 8
```

That is: normal workspaces stay on `workspace_id` (single-partition
ownership, ordering preserved as documented). High-volume workspaces
are split across up to 8 partitions per (workspace, session-hash
bucket). Ordering within a session is preserved (sessions never
cross buckets); cross-session ordering for a hot workspace is not,
which matches the analytical semantics we already offer.

The high-volume flag is on the `workspaces` row (`kafka_key_strategy`
column) and Aurora reads it via Cartograph's cached workspace
metadata endpoint. Flipping it is a runbook operation, not automatic
— it triggers a Kafka partition rebalance for the affected
consumer groups.

## Pulse

Two Pulse roles, deployed as separate Kubernetes deployments (same
image, different `PULSE_ROLE` env var):

### `pulse-enrich`

- Consumer group: `pulse-enrich`.
- Reads `events.raw`, writes `events.enriched`.
- Enrichment steps: UA parse, IP → geo (MaxMind), identity resolution
  (Redis-backed anonymous→user map), cohort tag lookup (Postgres,
  refreshed every 60s), Cartograph-driven property normalization.
- Failed enrichment (missing schema, poison payload) → `events.dlq`
  with reason header.

### `pulse-writer`

- Consumer group: `pulse-writer`.
- Reads `events.enriched`, batch-inserts ClickHouse.
- Batch policy: flush at **50,000 rows** or **2 seconds**, whichever
  first.
- Writes to the distributed table `events_all`; ClickHouse routes to
  the appropriate `events_local` shard based on the sharding key
  (`cityHash64(workspace_id)`).
- On ClickHouse degradation: exponential backoff, and after N
  attempts the batch spills to S3 (`meridian-events-archive/spill/`);
  Atlas replays from spill.

## DLQ handling

`events.dlq` is not customer-visible. On-call triages daily via
`scripts/dlq-summary.py` (ingest team). Common reasons: schema not
found, invalid property type, event name blacklisted, payload too
large. Repeat offenders bubble up as tickets to the customer's
solutions engineer.

## Config snippets

Consumer defaults (Pulse):

```yaml
kafka:
  bootstrap: b-1.msk-prod-uw2.mrdn.internal:9098,...
  auth: iam
  consumer:
    session.timeout.ms: 30000
    max.poll.records: 500
    enable.auto.commit: false
    isolation.level: read_committed
```

Producer defaults (Aurora):

```yaml
kafka:
  acks: all
  min.insync.replicas: 2
  compression.type: zstd
  linger.ms: 5
  batch.size: 131072
```
