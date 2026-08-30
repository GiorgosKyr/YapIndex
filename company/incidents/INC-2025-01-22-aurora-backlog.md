---
title: "INC-2025-01-22: Aurora ingest backlog, ~4h data delay"
category: incident
author: Wen Liu
team: Ingest
created: 2025-01-22
updated: 2025-01-23
status: resolved
version: 1.0
---

# INC-2025-01-22 — Aurora ingest backlog (Kafka partition skew)

- **Severity:** SEV-2
- **Status:** Resolved
- **Detected:** 2025-01-22 06:14 PT via Datadog monitor
  `dd:monitor/38471` (`aurora.kafka.consumer_lag > 300s`)
- **Resolved:** 2025-01-22 10:47 PT (query-visibility recovery)
- **PagerDuty:** PD-INC-C11908
- **Slack channel:** `#inc-2025-01-22`
- **Responders:** Wen Liu (IC, Ingest lead), Priya Ramanathan (Platform),
  Jae-won Park (Data, ClickHouse write-side), Ben Ortiz (SRE)

## Summary

At 06:14 PT, Datadog fired `pulse.kafka.consumer_lag > 300s` on partition 7
of `events.raw`. Aurora was ingesting cleanly (p99 well under SLO); the
lag was on Pulse's consumer side. Partition 7 had become dramatically
hot after a new large customer, **Buoyant Apparel**, cut over from their
pilot workspace to their production workspace overnight (~04:20 PT). Their
workspace id hashed onto partition 7, and their event volume was ~14x the
next-largest workspace on that partition. Pulse consumer for partition 7
saturated at ~92k events/sec and fell behind; other 11 partitions were
healthy at <10s lag.

Customer-facing impact: queries against `Beacon` returned results up to
~4 hours stale for any workspace whose events landed on partition 7.
Ingest itself did NOT drop events — everything landed in Kafka correctly.

## Impact

- **Workspaces with degraded query freshness:** 34 (all on partition 7).
- **Peak data delay:** 4h 12m at 09:30 PT.
- **Data loss:** None. All events were persisted in Kafka and eventually
  processed to ClickHouse.
- **SLO impact:** Query-freshness SLO (P99 < 90s) breached for the
  affected workspaces from 07:00 to 10:47 PT.

## Timeline (PT)

- **04:20** — Buoyant Apparel prod workspace cutover completes; their
  Aurora ingest ramps to ~92k events/sec sustained.
- **06:14** — `dd:monitor/38471` fires SEV-3 warn; auto-escalates SEV-2
  at 06:30 (lag still growing).
- **06:32** — Wen paged, joins `#inc-2025-01-22`.
- **06:40** — Wen identifies partition skew: `kafka-consumer-groups.sh
  --describe` shows partition 7 with 3.1M message lag, others <2k.
- **06:55** — Root cause narrowed to Buoyant workspace via Pulse trace
  sampling.
- **07:20** — Short-term mitigation: temporarily scaled `pulse-worker`
  StatefulSet from 12 → 24 replicas (only helps if partitions are also
  increased — Kafka consumer parallelism is bounded by partition count).
  Increased partition count of `events.raw` from 12 → 24 with
  `kafka-topics.sh --alter`. New partitions empty; existing skew persists
  on partition 7 until reassigned.
- **08:15** — Partition reassignment plan generated with
  `kafka-reassign-partitions.sh`; splitting Buoyant's workspace across
  partitions requires changing the partition key.
- **09:00** — Hotfix deployed in Aurora: for workspaces flagged
  `high_volume=true`, partition key changes from `hash(workspace_id)` to
  `hash(workspace_id + session_id)`. Buoyant marked `high_volume=true`.
- **09:15** — New events from Buoyant begin spreading across partitions.
  Existing backlog on partition 7 still draining.
- **10:47** — Consumer lag on partition 7 back under 60s. All workspaces
  current.

## Mitigation

1. Increased `events.raw` partitions from 12 → 24.
2. Introduced `high_volume` flag in Aurora with per-workspace partition
   key override (`hash(workspace_id + session_id)`).
3. Scaled `pulse-worker` back to 16 replicas (steady state).

## Follow-up

- Runbook: `runbooks/rebalance-kafka-partitions.md` (created 2025-01-24).
- Datadog monitor added: `dd:monitor/38512` — per-partition consumer lag
  alert (previously only alerted on aggregate consumer lag).
- Automated `high_volume` promotion evaluated but not implemented —
  currently manual, reviewed at onboarding.
