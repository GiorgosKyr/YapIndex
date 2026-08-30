---
title: Beacon-Aggregator — Query Caching
category: backend
author: elena.vasquez@meridiandata.io
team: Product Eng
created: 2022-08-30
updated: 2026-04-18
status: current
version: 2.4
---

# Beacon-Aggregator caching

Beacon-Aggregator ("agg") sits between Beacon and ClickHouse. Its whole
purpose is to serve as many dashboard reads as possible without touching
ClickHouse. It has two backing stores:

- **Redis** — hot, per-query-shape cache of the actual response bodies.
- **Postgres** — precomputed rollups (`rollups_hourly`, `rollups_daily`)
  written by Atlas and read by aggregator on cache miss.

Aggregator is a Python service (Product Eng). It listens on
`beacon-agg.internal:8080` and is only reachable from within the VPC.

## Cache key

The Redis key is:

```
agg:v3:{workspace_id}:{query_shape_hash}:{time_bucket}
```

- `query_shape_hash` — SHA-256 of a canonicalized form of the query DSL:
  metric, filters, group_by, interval, but **not** `time_range` (that lives
  in the bucket).
- `time_bucket` — the time bucket the query rounds down to. `last_hour`
  queries bucket to the current minute. Fixed ranges (e.g.
  `2026-07-01..2026-07-31`) bucket to the range endpoints. Rolling ranges
  (`last_7_days`) bucket to the current UTC hour.

Two customers issuing structurally identical queries hit different keys
because `workspace_id` is part of the prefix. There is no cross-workspace
sharing, ever — this is both a correctness and a security guarantee.

## TTLs

| Query flavor                   | TTL     |
|--------------------------------|---------|
| `last_hour` (fine-grained)     | 60s     |
| `last_24h`                     | 15 min  |
| `last_7_days`, `last_30_days`  | 15 min  |
| Fixed historical ranges        | 24 h    |
| Cohort membership snapshots    | 6 h     |

Most queries land at 15 minutes. The 1-minute TTL on `last_hour` exists so
customers watching a live dashboard see numbers move within a minute or
two of new events arriving; anything shorter and we spend more compute
warming the cache than serving from it.

## Precomputed rollups

On cache miss, aggregator tries the Postgres rollup tables before falling
through to ClickHouse:

- `rollups_hourly(workspace_id, metric, hour_ts, dimensions_json, value)`
- `rollups_daily(workspace_id, metric, day, dimensions_json, value)`

Atlas populates these nightly (`rollups_daily`) and every 15 minutes
(`rollups_hourly`) via Airflow DAGs. If a query can be served from a
rollup — i.e. its `group_by` matches indexed dimensions and its
`time_range` aligns to hour or day boundaries — aggregator does it there
and skips ClickHouse. This handles roughly two-thirds of dashboard reads.

Example lookup:

```python
async def try_rollups(workspace_id: str, q: QueryRequest) -> QueryResponse | None:
    if not q.aligns_to_hour_boundary():
        return None
    rows = await pg.fetch(
        """
        SELECT hour_ts, dimensions_json, value
          FROM rollups_hourly
         WHERE workspace_id = $1
           AND metric       = $2
           AND hour_ts     >= $3
           AND hour_ts      < $4
        """,
        workspace_id, q.metric, q.range_start, q.range_end,
    )
    if not rows:
        return None
    return _shape(rows, q)
```

## Historical context on Redis

Redis was **originally** introduced in July 2020 for session caching
(see ADR-0001, informal). Its use for query result caching came later,
in the second half of 2022, when Beacon-Aggregator was built and needed a
fast per-key store. Both uses still coexist in the same ElastiCache
cluster on separate keyspaces (`sess:*` vs `agg:*`).

There is a runbook (`runbooks/redis-capacity.md`) that describes Redis
"primarily" as a rate-limiting store. That runbook has not been rewritten
since 2023 and is out of date; rate limiting is one use, but not the
primary one. Do not attempt to reconcile this document with that
runbook — the discrepancy is known and is being tracked separately.

## Related

- `backend/beacon-service.md`
- `adrs/0001-redis-for-session-caching.md`
- `runbooks/redis-capacity.md` (stale on the primary-purpose question)
