---
title: ClickHouse Node Recovery
category: runbook
author: Jae-won Park
team: Data
created: 2024-10-02
updated: 2026-02-19
status: current
version: 2.1
---

# ClickHouse Node Recovery

Recover a failed node in the 6-node ClickHouse cluster
(`clickhouse-prod-{1..6}`) running on EKS. Covers unresponsive-node
recovery, replica resync from a healthy shard peer, and full restore from
S3 backup.

The "query cost limit" section (step 5) was added after INC-2026-02-03,
when Atlas ran an unbounded `SELECT` against `clickhouse-prod-3` and OOM-
killed the node during Q4 report generation.

## Preconditions

- Platform or Data on-call.
- `kubectl` context set to `meridian-prod` EKS cluster.
- `clickhouse-client` available on a jump pod
  (`kubectl -n clickhouse exec -it ch-tools -- bash`).
- `clickhouse-backup` CLI configured against the
  `meridian-clickhouse-backups` S3 bucket
  (backups run nightly at 02:15 UTC, retention 14 days).
- ZooKeeper ensemble is healthy — check
  `kubectl -n zookeeper exec -it zk-0 -- zkServer.sh status` on all 3
  members. (Migration to ClickHouse Keeper is on the Q1 2027 roadmap;
  until then, a broken ZK is a blocker.)

## Steps

### 1. Confirm the node is actually down

```bash
kubectl -n clickhouse get pods -l app=clickhouse-prod
```

Look for `CrashLoopBackOff`, `Pending`, or `Running` with `0/1 Ready`.

From a healthy peer, confirm it dropped out of the cluster:
```sql
SELECT host_name, is_alive
FROM system.clusters
WHERE cluster = 'meridian_prod';
```

### 2. Grab logs before rebooting anything

```bash
kubectl -n clickhouse logs clickhouse-prod-<N> --previous > /tmp/ch-<N>.log
```

Attach to the incident channel. Common failure modes:
- `Cannot allocate memory` → OOM (see step 5).
- `Suspiciously many broken parts` → disk / merge corruption; skip to
  step 4 (restore).
- `Cannot connect to ZooKeeper` → ZK problem, not a node problem.

### 3. Replica resync from a healthy peer

If the node process is alive but replicas are lagging:

1. Enter the affected node:
   ```bash
   kubectl -n clickhouse exec -it clickhouse-prod-<N> -- clickhouse-client
   ```
2. Force a replica sync per replicated table:
   ```sql
   SYSTEM SYNC REPLICA events;
   SYSTEM SYNC REPLICA events_enriched;
   SYSTEM RESTART REPLICA events;
   ```
3. Watch `system.replicas`:
   ```sql
   SELECT table, log_max_index, log_pointer,
          absolute_delay, queue_size
   FROM system.replicas;
   ```
   `absolute_delay` should decrease to 0. If `queue_size` is growing,
   escalate — the replica cannot catch up from live writes and needs a
   full restore.

### 4. Full restore from S3 backup

Use when the local `/var/lib/clickhouse/store` is corrupt, or the EBS
volume was lost.

1. Cordon and drain the node:
   ```bash
   kubectl cordon <ch-node>
   kubectl -n clickhouse delete pod clickhouse-prod-<N> --grace-period=30
   ```
2. Wipe and reattach the data volume, or provision a new PVC.
3. Restore the latest backup:
   ```bash
   kubectl -n clickhouse exec -it clickhouse-prod-<N> -- \
     clickhouse-backup restore_remote latest-nightly \
     --schema --data --rm
   ```
   Expected output ends with:
   ```
   done backup=latest-nightly operation=restore duration=27m14s
   ```
4. Restart the pod; ClickHouse will re-register with ZooKeeper and begin
   pulling any deltas since the backup.
5. Re-run step 3's sync check.

### 5. Query cost limit (added after INC-2026-02-03)

Before returning the node to full traffic, confirm the per-user cost
guards are active. They were reset in INC-2026-02-03 by a bad Kustomize
overlay.

```sql
SELECT name, value
FROM system.settings
WHERE name IN (
  'max_memory_usage',
  'max_memory_usage_for_user',
  'max_execution_time',
  'max_bytes_to_read'
);
```

Expected in `prod`:
- `max_memory_usage` = 8 GiB
- `max_memory_usage_for_user` = 24 GiB (Atlas exports run here)
- `max_execution_time` = 900 s
- `max_bytes_to_read` = 500 GiB

If any value is 0 or default, apply the profile overlay:
```bash
kubectl -n clickhouse apply -f manifests/prod/query-cost-profile.yaml
```
and issue `SYSTEM RELOAD CONFIG`.

## Verification

- `SELECT * FROM system.clusters WHERE cluster='meridian_prod'` — all 6
  nodes `is_alive = 1`.
- Datadog dashboard `data / clickhouse cluster` — replication lag zero
  for 15 min.
- Pulse consumer lag is not backing up.
- A canary query from Beacon returns within p95 baseline.

## Rollback

If restore introduces corruption or wrong data version:
- Bring the node back down (`kubectl scale ... --replicas=0` for the
  StatefulSet slice, or cordon + delete).
- Restore a specific older backup:
  `clickhouse-backup restore_remote <backup-name>`.
- The other 5 nodes continue serving reads. Writes have replication
  factor 2 so a single missing node does not drop data.

## Contacts

- Data on-call: `@data-oncall` in `#eng-oncall`
- Data lead: Jae-won Park
- Escalation: Priya Ramanathan (Platform, ZooKeeper), Ben Ortiz (SRE)
