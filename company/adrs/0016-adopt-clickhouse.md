---
title: "ADR-0016: Adopt ClickHouse for event analytics"
category: adr
author: Jae-won Park
team: Data
created: 2022-06-09
updated: 2024-04-22
status: current
version: 1.3
---

# ADR-0016: Adopt ClickHouse for event analytics

## Status

**Accepted** — 2022-06-09. Signed off by Ravi Patel (CTO) and Jae-won
Park (Head of Data).

Note: This ADR describes the initial 4-node deployment on EC2. The
cluster grew to 6 nodes in 2024 and was moved onto EKS as part of the
March 2024 ECS→EKS migration (see ADR-0031). Those changes did not
require re-litigating this decision.

## Context

Follows directly from ADR-0014, in which we rejected Snowflake for
customer-facing analytics. Postgres aggregate queries powering the
customer dashboards continue to degrade; a full re-write onto a purpose-
built OLAP engine is required before Q3 2022.

Shortlist from ADR-0014: ClickHouse (self-hosted), Apache Druid,
TimescaleDB.

Benchmarks over 6 weeks against a representative workload (30 days of
events for our three largest workspaces, 4 dashboard queries per
workspace, 50 concurrent users):

| Engine | p50 | p95 | p99 | Cost/mo (self-run est.) |
|--------|-----|-----|-----|--------------------------|
| Postgres (baseline) | 480 ms | 4200 ms | 12000 ms | current |
| TimescaleDB | 220 ms | 1400 ms | 4800 ms | ~$3.2k |
| Druid | 90 ms | 380 ms | 900 ms | ~$8k + JVM ops load |
| ClickHouse (4-node) | 60 ms | 240 ms | 620 ms | ~$4.5k |

ClickHouse won on latency, cost, and — despite the ZooKeeper
dependency — team fit. We already have Go and Python operators; nobody
is excited about running Druid's Coordinator/Overlord/Historical/Broker
mesh in production.

## Decision

Adopt **ClickHouse 22.3 LTS** as the analytics store for customer-facing
dashboards.

Initial topology:
- **4-node** self-hosted cluster on EC2 (`r5.4xlarge`), in a dedicated
  security group, in `us-west-2`.
- 2 shards × 2 replicas.
- ZooKeeper ensemble (3 nodes on `t3.medium`) for replication metadata.
- Managed backups to `s3://meridian-clickhouse-backups` nightly.
- No public ingress. Access only from Beacon, Atlas, and jump pods.

Migration path:
- Dual-write from the Django ingest path into both Postgres event tables
  and ClickHouse for a 4-week bake period.
- Beacon reads switched over per-endpoint behind a feature flag.
- Postgres event tables drop-tabled once all endpoints have been on
  ClickHouse for 30 days without incident.

Schema owner: Data team. Schema changes go through migration review with
Cartograph maintainers because customer event schemas can synthesize
ClickHouse columns.

## Consequences

Positive:
- 20-70× latency improvement across the dashboard workload.
- Compression and columnar storage cut event-store cost roughly 5× vs.
  Postgres.
- Gives us headroom to onboard Enterprise-scale customers without
  re-architecting again.

Negative / operational cost:
- We now run a distributed OLAP database, with all that implies:
  replication lag, part merges, ZooKeeper (a well-known ops footgun),
  and OOM behavior under bad queries.
- Backups and restores are more involved than Postgres; a full runbook
  is a follow-up deliverable.
- Adds ~$4.5k/month infra spend at Q3-2022 scale. Still far below the
  Snowflake projection from ADR-0014.

Follow-ups:
- Cluster grew from 4 → 6 nodes in 2024 as event volume tripled.
- Move to EKS bundled with ADR-0031.
- ZooKeeper → ClickHouse Keeper migration is on the Q1 2027 roadmap
  (canon §11) — will get its own ADR when it lands.
- Per-user query cost limits were tightened after INC-2026-02-03; see
  `runbooks/clickhouse-node-recovery.md` § 5.
