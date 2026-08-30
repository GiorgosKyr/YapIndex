---
title: Kafka Partition Rebalance (Hot Partition Recovery)
category: runbook
author: Wen Liu
team: Ingest
created: 2025-01-30
updated: 2026-01-08
status: current
version: 1.4
---

# Kafka Partition Rebalance (Hot Partition Recovery)

Written after INC-2025-01-22, when a single large customer caused all their
events to hash to one partition on `events.raw`, backing up Aurora →
Pulse ingest for four hours.

Use this runbook when:

- Datadog dashboard `ingest / kafka partition health` shows one or more
  partitions on `events.raw` (or `events.enriched`) with lag > 5× the
  cluster median for > 5 min.
- Pulse consumer group lag alarm has fired (`pulse-consumer-lag-high`).
- Aurora ingress latency p95 is elevated but broker CPU is normal — the
  bottleneck is downstream partition-level.

## Preconditions

- You are Platform on-call or Ingest team.
- You have MSK admin creds via `aws-vault exec meridian-prod-msk`.
- Access to a jump pod with `kafka-consumer-groups.sh` and
  `kafka-reassign-partitions.sh` (image
  `ecr/meridian/msk-tools:2.9.0`).
- You have the current partition count for the topic
  (`events.raw` = 48 partitions as of 2026-01).

## Steps

### 1. Diagnose which partition(s) are hot

1. On the jump pod:
   ```bash
   kubectl -n ingest exec -it msk-tools -- \
     kafka-consumer-groups.sh \
     --bootstrap-server $BOOTSTRAP \
     --describe --group pulse-events-raw
   ```
   Expected columns: `TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG`.
   Sort by `LAG`. Anything > 5× the median across partitions is hot.
2. Cross-check with Datadog dashboard `ingest / kafka partition health`
   (widget "Lag by partition, top 10").
3. Identify the workspace(s) driving the hot partition by joining Pulse
   logs on `partition_id`:
   ```
   service:pulse "partition=<N>" | top 10 by @workspace_id
   ```
   In INC-2025-01-22 this was a single Enterprise workspace.

### 2. Decide whether to rebalance now

- **Do not** run reassignment during peak traffic (weekdays 08:00–17:00 PT
  or 13:00–22:00 GMT) unless you have declared a SEV. Reassignment doubles
  network throughput on affected brokers while data is copied.
- Prefer the short-term mitigations in step 3 during peak, and schedule
  the reassignment for the next off-peak window.

### 3. Short-term mitigation

- Bump Pulse consumer replicas for the hot workspace: edit
  `overlays/prod/pulse/hpa.yaml`, raise `maxReplicas` from 12 → 24, merge
  via the standard deploy path.
- If a single workspace is producing > 40% of traffic, temporarily route
  it to the overflow topic `events.raw.overflow` by flipping the
  LaunchDarkly flag `ingest.workspace_overflow_route` for that workspace
  ID.

### 4. Reassignment (off-peak)

1. Generate a candidate assignment. Create
   `/tmp/hot-partitions.json`:
   ```json
   {
     "version": 1,
     "topics": [{"topic": "events.raw"}]
   }
   ```
2. Ask Kafka for a new distribution:
   ```bash
   kafka-reassign-partitions.sh \
     --bootstrap-server $BOOTSTRAP \
     --topics-to-move-json-file /tmp/hot-partitions.json \
     --broker-list "1,2,3,4,5,6,7,8,9,10,11,12" \
     --generate > /tmp/reassign-plan.json
   ```
3. Review `Proposed partition reassignment configuration`. Save just that
   block as `/tmp/reassign-execute.json`.
4. Execute:
   ```bash
   kafka-reassign-partitions.sh \
     --bootstrap-server $BOOTSTRAP \
     --reassignment-json-file /tmp/reassign-execute.json \
     --execute --throttle 50000000
   ```
   The 50 MB/s throttle keeps replication from starving live traffic.
5. Poll progress:
   ```bash
   kafka-reassign-partitions.sh \
     --bootstrap-server $BOOTSTRAP \
     --reassignment-json-file /tmp/reassign-execute.json --verify
   ```
   Expect all partitions to report `completed successfully` within
   30-90 min depending on data volume.

### 5. Workspace-key remapping (long-term)

If the same workspace repeatedly hot-spots, add it to the
`WORKSPACE_KEY_SALT_OVERRIDES` map in Aurora
(`internal/partition/key.go`), which adds a per-workspace salt so events
distribute across N partitions instead of hashing to one. Requires an
Aurora deploy.

## Verification

- `kafka-consumer-groups.sh --describe` shows lag falling within 15 min.
- Datadog `ingest / kafka partition health` — max partition lag returns to
  within 2× median.
- No new pages on `pulse-consumer-lag-high` for 30 min.

## Rollback

- Reassignment can be canceled mid-flight:
  ```bash
  kafka-reassign-partitions.sh --bootstrap-server $BOOTSTRAP --cancel
  ```
- Salt override rollback: revert the Aurora commit and redeploy.

## Contacts

- Ingest on-call: `@ingest-oncall`
- Escalation: Wen Liu (Ingest lead) → Priya Ramanathan (Platform)
- MSK vendor: AWS Premium Support case, priority `production-down`
