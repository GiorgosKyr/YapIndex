---
title: "ADR-0022: Introduce Kafka (MSK) between Aurora and ClickHouse"
category: adr
author: Ravi Patel
team: Platform
created: 2023-03-14
updated: 2023-03-21
status: Accepted
version: 1.0
---

# ADR-0022: Introduce Kafka (MSK) between Aurora and ClickHouse

## Context

Aurora (then called `ingest-api`) currently writes accepted events directly
to ClickHouse in 5-second micro-batches. This has worked well through
mid-2022 but is starting to hurt:

- **No back-pressure.** A slow ClickHouse insert causes Aurora request
  latency to spike, which pushes back on customer SDKs. We've had four
  near-misses in Q1 alone.
- **No replay.** If Pulse enrichment logic changes (geoip corrections,
  schema fixes) we can't re-derive `events.enriched` because we have no
  buffered raw stream.
- **Coupled deploys.** Any ClickHouse schema change requires coordinated
  release with `ingest-api`.
- **No fan-out.** We now want a second consumer (Cartograph schema
  validation) reading the same event stream.

## Decision

Introduce Apache Kafka via AWS MSK. Insert a topic `events.raw` between
Aurora (producer) and a new stream-processor consumer (later named
**Pulse**). Pulse handles enrichment and writes to `events.enriched`,
which a batch writer flushes to ClickHouse.

Topic layout:

- `events.raw`: 48 partitions (starting), key = `workspace_id`, retention 3 days
- `events.enriched`: 48 partitions, key = `workspace_id`, retention 7 days
- `events.dlq`: 8 partitions, retention 14 days

MSK cluster: 6 brokers `kafka.m5.xlarge` in 3 AZs, IAM auth (no SASL/SCRAM).

## Alternatives considered

- **Kinesis Data Streams.** Simpler ops but 24h retention max on standard
  tier, and we want longer replay windows. Also we want partition-level
  ordering semantics that map cleanly to consumer groups.
- **Redpanda.** Attractive (no ZK, single binary). Not yet enterprise-ready
  in AWS-managed form. Revisit in 12 months.
- **Postgres LOGICAL replication as event bus.** Explored briefly, dismissed.
  Not designed for this volume.

## Consequences

**Positive:**
- Decouples Aurora latency from ClickHouse ingest latency.
- Enables replay, fan-out, and dead-lettering.
- Pulse can be scaled independently.

**Negative:**
- New operational surface (MSK, ZooKeeper).
- Higher end-to-end latency: est. +2s p50 ingest→queryable (accepted).
- Cost: ~$5K/mo MSK infrastructure.

## Follow-ups

- Runbook for consumer-lag alerts.
- Backfill tooling to re-enrich from `events.raw` on demand.
- Later: partition-count grew to 96 in 2024; hot-key mitigation added
  after [INC-2025-01-22](../incidents/INC-2025-01-22-aurora-backlog.md).

## Status

Accepted, 2023-03-21. Implemented in 2023 Q2. Production cutover 2023-06-08.
