---
title: Meeting notes — INC-2026-02-03 ClickHouse OOM review
category: meeting-notes
author: Jae-won Park
team: Data
created: 2026-02-04
updated: 2026-02-04
status: current
version: 1.0
---

# 2026-02-04 — ClickHouse OOM post-incident review

Zoom. ~35 min. Blameless.

## Attendees
- Jae-won Park (Data, chair)
- Priya Ramanathan (Platform)
- Ben Ortiz (SRE)
- Marcus Oduya (VP Eng)

## Timeline (short)
- 2026-02-03 02:14 PT: Atlas kicked off the Q4 export job (Airflow DAG
  `atlas_q4_export`).
- 02:17 PT: query landed on `clickhouse-prod-3` — a `SELECT ... GROUP BY
  workspace_id, event_name, day` across the full `events.enriched`
  table for Q4 (no partition prune on the outer join).
- 02:44 PT: `clickhouse-prod-3` OOM-killed by kubelet. Cluster degraded
  to 5/6 nodes.
- 02:46 PT: PD paged Platform (Ben, secondary was Wen).
- 02:52 PT: Ben identified the query in system.processes on the peers,
  killed the retry.
- 03:11 PT: `clickhouse-prod-3` back, distributed table healthy.
- No customer-facing impact — reads degraded but continued via other
  nodes. Portal p99 spiked briefly.

## Root cause
- Atlas has no per-query memory/cost limit configured. The Q4 export
  DAG was newly added in January by the analytics team and its query
  wasn't reviewed against ClickHouse cost.
- Cluster-level `max_memory_usage_for_user` is set but the query still
  fit under it right up to the point of OOM. Kubelet killed the pod
  before the query hit the ClickHouse-side limit — memory accounting
  discrepancy.

## Discussion

- Jae-won: this is the second Atlas-driven query surprise this quarter.
  Time to make Atlas respect explicit cost limits, not rely on
  ClickHouse to protect itself.
- Priya: we should push cost limits into the query at Atlas layer:
  `SET max_memory_usage = <n>` + `SET max_execution_time = <n>` at
  session start for every Atlas DAG. Default conservative, override
  per-DAG with justification.
- Ben: also want a Datadog monitor on ClickHouse pod memory that
  pre-empts before kubelet. Threshold TBD.
- Marcus: who owns Atlas — is this Data or Platform? Jae-won: Data owns
  it. (Aside: there's persistent confusion in some docs about Aurora
  ownership too — Ingest, not Platform. Separate issue but noted.)
- Priya: the analytics DAG in question — is that a workspace or is it
  cross-tenant? Jae-won: cross-tenant (internal analytics). Fine,
  scoping isn't the issue; the query shape is.
- Ben: no need for a public postmortem. Note in `#status` if any
  customer asks about the p99 spike.

## Action items
- [ ] Jae-won — add cost-limit wrapper to Atlas DAG runner
      (`SET max_memory_usage`, `SET max_execution_time`, `SET
      max_bytes_before_external_group_by`), default values documented
      in ADR. Draft by 2026-02-11.
- [ ] Jae-won — write a short ADR (probably ADR-0051 or so) — "Atlas
      query cost limits". Data team owns.
- [ ] Ben — Datadog monitor: ClickHouse pod memory > 85% for 5min,
      warn; > 92% for 2min, page. In place by 2026-02-07.
- [ ] Priya — review PDBs on ClickHouse StatefulSet — we lost one node
      and were fine but let's confirm we could tolerate two.
- [ ] Marcus — chase Data team to review any other recently-added DAGs
      for the same footgun.

## Not action items
- ClickHouse Keeper migration (off ZooKeeper) is planned Q1 2027 — not
  related to this incident, just noting since it came up.
