---
title: "INC-2026-02-03: ClickHouse OOM during Q4 report generation"
category: incident
author: Jae-won Park
team: Data
created: 2026-02-03
updated: 2026-02-04
status: resolved
version: 1.0
---

# INC-2026-02-03 — ClickHouse OOM on `clickhouse-prod-3`

- **Severity:** SEV-2
- **Status:** Resolved
- **Detected:** 2026-02-03 02:41 PT via
  `dd:monitor/57104` (`clickhouse.node.oom_kill_count > 0`) and
  `dd:monitor/57108` (`beacon.query.p99 > 5s`)
- **Resolved:** 2026-02-03 04:12 PT
- **PagerDuty:** PD-INC-G05581
- **Slack channel:** `#inc-2026-02-03`
- **Responders:** Jae-won Park (IC), Priya Ramanathan (Platform), Ben
  Ortiz (SRE), Elena Vasquez (query-side impact)

## Summary

During the Sunday nightly export window, an Atlas job
(`atlas.jobs.q4_report_customer_rollup`) executed a `SELECT` against
`clickhouse-prod-3` with no memory or row-count bound. The query
attempted to materialize ~4.8B rows in-memory. The `clickhouse-server`
process was OOM-killed by the kernel at 02:41 PT. Systemd restarted
the process ~40s later, but the node re-joined the cluster degraded
and re-ran distributed sub-queries slower than usual for ~90 minutes.
The five other nodes handled traffic during the outage; the cluster
did not go fully down.

## Impact

- **Beacon query p99:** 380ms → 5.2s at peak (03:15 PT).
- **Portal:** dashboards slower to load; no 5xx.
- **Atlas job:** `q4_report_customer_rollup` failed; retried after
  fix. Q4 export delivery to customer S3 buckets delayed by ~6h
  (delivered 2026-02-03 morning).
- **Data loss:** None. Ingest continued via Pulse writing to healthy
  nodes.
- **SLO impact:** Beacon query-latency SLO breached for the window.

## Timeline (PT)

- **02:00** — Atlas nightly window begins.
- **02:17** — `q4_report_customer_rollup` starts on
  `clickhouse-prod-3`. Query plan estimates ~4.8B rows.
- **02:38** — `clickhouse-server` memory usage on node-3 hits
  ~58GB / 62GB.
- **02:41** — OOM killer terminates `clickhouse-server`.
  `dd:monitor/57104` fires.
- **02:42** — Jae-won paged. Joins `#inc-2026-02-03`.
- **02:44** — systemd restarts `clickhouse-server`. Node re-joins
  cluster in ~40s.
- **02:50** — Jae-won identifies the offending query in
  `system.query_log` on the surviving nodes; traces to Atlas job.
- **03:00** — Atlas job killed; job disabled in Airflow pending fix.
- **03:15** — Beacon p99 peaks at 5.2s as node-3 catches up on
  distributed reads. Cluster otherwise nominal.
- **04:00** — node-3 fully caught up.
- **04:12** — Incident closed.

## Mitigation

1. Offending Atlas job disabled in Airflow.
2. Query rewritten to chunk by `toYYYYMM(event_date)` and stream
   results via `FORMAT JSONEachRow` to S3.
3. Ad-hoc: added `SETTINGS max_memory_usage=8000000000,
   max_execution_time=600` to the rewritten query as a bound.

## Follow-up

Full postmortem: `postmortems/2026-02-03-clickhouse-oom.md`.
See `backend/pulse-service.md` for the ingest side and
`architecture/event-pipeline.md` for cluster topology.
