---
title: ClickHouse Schema — events cluster
category: database
author: Jae-won Park
team: Data
created: 2022-07-08
updated: 2026-06-30
status: current
version: 3.1
---

# ClickHouse Schema — events cluster

The ClickHouse cluster is the analytical store behind Beacon and every
report/cohort/funnel query in Portal. It was adopted in mid-2022 to replace
the Postgres aggregate queries that had started to buckle under load
(see ADR-0016). The 2023 scale-out project was internally codenamed
"Kraken" — that's not a service, it's just the ClickHouse migration.

## Topology

Six nodes: `clickhouse-prod-0` through `clickhouse-prod-5`, running
ClickHouse 24.3 on EKS in `us-west-2` (three shards, two replicas each).
ZooKeeper coordinates replication today; the Q1 2027 roadmap moves us to
ClickHouse Keeper.

> **OUTDATED note preserved from the 2023 handbook:** "The cluster runs on
> 4 nodes (`clickhouse-prod-0` through `-3`)." This is no longer accurate —
> the cluster was scaled out to 6 nodes as part of the "Kraken" work
> tracked under ADR-0016 and follow-on capacity planning. The canonical
> topology is 6 nodes, three shards × two replicas.

## Main table: `events`

`events` is a `ReplicatedMergeTree` partitioned by month and ordered by
`(workspace_id, event_ts, event_id)`. The ordering key was chosen so that
per-workspace scans (the overwhelming majority of query traffic from
Beacon) touch contiguous parts.

```sql
CREATE TABLE events ON CLUSTER meridian
(
    workspace_id   UUID,
    event_id       UUID,
    event_ts       DateTime64(3, 'UTC'),
    received_ts    DateTime64(3, 'UTC'),
    event_name     LowCardinality(String),
    user_id        String,
    anon_id        String,
    session_id     String,
    properties     Map(LowCardinality(String), String),
    revenue_cents  Nullable(Int64),
    schema_version UInt16
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events',
    '{replica}'
)
PARTITION BY toYYYYMM(event_ts)
ORDER BY (workspace_id, event_ts, event_id)
TTL toDate(event_ts) + INTERVAL 25 MONTH
SETTINGS index_granularity = 8192;
```

Pulse (`pulse-worker`) is the only writer. Aurora used to write directly
before ADR-0022 introduced Kafka.

## Materialized views (rollups)

Two rollup tables power Beacon-Aggregator. They are materialized views over
`events`, aggregated with `SummingMergeTree` and `AggregatingMergeTree` as
appropriate.

- `events_hourly` — `(workspace_id, event_name, hour)` → counts, uniq users,
  sum revenue. Feeds most Portal dashboard widgets.
- `events_daily` — `(workspace_id, event_name, day)` → same, with 90 days
  of quantile sketches for latency-style properties.

```sql
CREATE MATERIALIZED VIEW events_hourly_mv ON CLUSTER meridian
TO events_hourly
AS
SELECT
    workspace_id,
    event_name,
    toStartOfHour(event_ts) AS hour,
    count()                 AS events,
    uniqState(user_id)      AS users_state,
    sumIfState(revenue_cents, revenue_cents IS NOT NULL) AS revenue_state
FROM events
GROUP BY workspace_id, event_name, hour;
```

## Retention

Row-level TTL keeps 25 months of `events`. Hourly rollups: 25 months.
Daily rollups: retained indefinitely (they are small).

For long-term storage beyond 25 months, Atlas exports monthly parquet to
`s3://meridian-events-archive/` (nightly job).

## Backups

See `database/database-backup-policy.md`. `clickhouse-backup` runs against
one replica per shard so we don't double-count storage.

## Operational notes

- Do NOT run unbounded `SELECT *` — that's what caused INC-2026-02-03
  (Atlas OOM'd `clickhouse-prod-3`). Every scan should have a
  `workspace_id` predicate and a bounded `event_ts` range.
- Query timeouts: Beacon sets `max_execution_time = 25s` per user query;
  Atlas jobs set 15 min.
- Cross-shard `JOIN` is expensive — prefer `GLOBAL IN` for lookups.
- Alter operations run via `ON CLUSTER meridian`; wait for
  `system.mutations` to drain before merging follow-on migrations.

## Related

- `database/postgres-schema.md` (OLTP metadata; `workspaces`, `schemas`)
- `api/api-v3-reference.md` (endpoints that read from ClickHouse via Beacon)
