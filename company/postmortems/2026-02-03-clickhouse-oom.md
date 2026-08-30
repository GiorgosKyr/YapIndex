---
title: Postmortem — ClickHouse OOM during Q4 Exports (INC-2026-02-03)
category: postmortem
author: Jae-won Park
team: Data
created: 2026-02-17
updated: 2026-02-24
status: current
version: 1.1
---

# Postmortem: ClickHouse OOM during Q4 Exports

**Incident:** [INC-2026-02-03](../incidents/INC-2026-02-03-clickhouse-oom.md)
**Severity:** SEV-2
**Duration:** ~90 min degraded query latency; ~22 min a full node was down.
**Author:** Jae-won Park (Data)
**Reviewers:** Priya Ramanathan, Ben Ortiz, Marcus Oduya
**Meeting:** [2026-02-04 review](../meetings/2026-02-04-clickhouse-oom-review.md)

## Summary

At 03:41 UTC on 2026-02-03, `clickhouse-prod-3` was OOM-killed by the Linux
kernel while an Atlas nightly export job ran an unbounded `SELECT` over the
`events` table for the year-end range. The node came back at 04:03 UTC.
Cluster remained available (5 of 6 nodes) but query latency was elevated
until 05:12 UTC as replicas caught up and the query load rebalanced.

## Impact

- ~22 min: `clickhouse-prod-3` completely offline.
- ~90 min: p99 query latency on `beacon` elevated from ~800ms to ~4.2s.
- Six customer-triggered reports failed with `BCN-5003` (query timeout);
  four were auto-retried and succeeded.
- No data loss. Ingest was unaffected (writes go through Pulse batching
  and buffered during the outage).

## Timeline (UTC)

| Time | Event |
|------|-------|
| 03:20 | Atlas job `atlas-yearly-exports-2025` starts. |
| 03:41 | Datadog alert `clickhouse.node.memory > 90%` fires. |
| 03:42 | `clickhouse-prod-3` OOM-killed. |
| 03:43 | PagerDuty pages Ben Ortiz (Platform primary). |
| 03:47 | Ben joins `#inc-2026-02-03`. Jae-won paged as SME. |
| 03:52 | Root cause suspected: Atlas query. Kill query issued (already dead with the node). |
| 04:03 | Node restarted, replicas catching up. |
| 04:12 | Beacon query latency starts recovering. |
| 05:12 | All p99 alerts clear. Incident resolved. |

## Root cause

The Atlas nightly export job constructs a `SELECT` that pulls the full year's
events for each customer for the annual usage report. The query lacked
`max_memory_usage`, `max_execution_time`, and `max_bytes_before_external_group_by`
settings, and used `GROUP BY` on a high-cardinality tuple. For the largest
tenant (Buoyant Apparel, ~2.1B rows in scope), the query exceeded ~40 GB of
resident memory on the coordinator replica and got OOM-killed.

## Contributing factors

1. **No per-query resource limits.** Atlas connected as user `atlas_writer`
   whose profile had no `max_memory_usage` set. All limits inherited defaults.
2. **No progressive alerting.** We alert on node memory `>90%` but not on
   individual query memory. We had ~7 minutes of warning we didn't use.
3. **Yearly reports were not load-tested.** This was the first time the
   yearly export ran against a full year of the new event schema (schema
   changed in 2025 Q3 to include `session_id`).
4. **Coordinator replica singled out.** `clickhouse-prod-3` happens to be
   the coordinator for Buoyant Apparel's shard, making it disproportionately
   hit.

## What went well

- Alerts fired fast (~1 min before OOM).
- Blameless response, clear ownership (Ben as IC, Jae-won as SME).
- No customer data loss.
- Ingest pipeline gracefully buffered during the degradation.

## What went poorly

- The `atlas_writer` role never got the query cost limits we said we'd apply
  in 2025 Q4 planning. This was carried in `ENG-4128` and forgotten.
- Runbook for a lost ClickHouse node was out of date; Ben spent ~4 min
  re-reading before acting.

## Action items

| # | Item | Owner | Due | Status |
|---|------|-------|-----|--------|
| 1 | Set `max_memory_usage=8G`, `max_execution_time=600` on `atlas_writer` profile | Jae-won | 2026-02-06 | done |
| 2 | Add Datadog monitor for any query using >70% node memory for 60s | Ben | 2026-02-13 | done |
| 3 | Refresh `runbooks/clickhouse-node-recovery.md` with post-2025 CH 24 syntax | Jae-won | 2026-02-20 | done |
| 4 | Investigate ClickHouse Keeper migration (removes ZK as SPOF) | Priya | 2026-Q3 | in-progress |
| 5 | Load-test yearly export against copy of prod | Data team | 2026-03-31 | done |

## Related documents

- Incident: `incidents/INC-2026-02-03-clickhouse-oom.md`
- Runbook: `runbooks/clickhouse-node-recovery.md`
- Service: `backend/pulse-service.md`
- Architecture: `architecture/event-pipeline.md`
- Prior CH scale-out decision: `adrs/0016-adopt-clickhouse.md`
