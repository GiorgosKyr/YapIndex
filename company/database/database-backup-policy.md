---
title: Database Backup Policy
category: database
author: Ben Ortiz
team: SRE
created: 2024-06-05
updated: 2026-06-01
status: current
version: 3.0
---

# Database Backup Policy

Every persistent datastore at Meridian has a defined backup policy. This
document is the reference for what those policies are, where the backups
live, how long we keep them, and how often we prove they work.

Redis is deliberately treated as a cache — see `database/redis-usage.md`
and the "Redis" section below.

## Postgres (`meridian_app`, `meridian_gatekeeper`)

- **Automated snapshots:** RDS snapshot every hour, retained for 35 days.
- **PITR (point-in-time recovery):** enabled, 35-day window. WAL is
  continuously shipped to S3 by RDS.
- **Cross-region copy:** the most recent automated snapshot is copied
  daily to `us-east-1` (our DR region) and retained for 35 days there
  too. This is a warm-standby posture — see canon §6.
- **Manual snapshots:** taken before major schema migrations and before
  major version upgrades. Retained 90 days.

Restore RTO target: 60 minutes for a full-instance restore from the most
recent snapshot. Restore RPO: 5 minutes via PITR under normal operation.

## ClickHouse (events cluster)

- **Tool:** `clickhouse-backup` (Altinity).
- **Schedule:** full backup daily at 03:00 UTC, hourly incremental for
  the last 24 hours.
- **Storage:** `s3://meridian-clickhouse-backups/` (versioned, lifecycle
  transitions to Glacier after 14 days).
- **Retention:** 30 days.
- **Scope:** one replica per shard participates, so we don't back up the
  same data twice.

Restore RTO target: 4 hours for the full cluster from S3. This is
deliberately looser than Postgres — the ClickHouse cluster can be
partially rebuilt from Kafka replay (7-day retention on `events.raw`)
plus Atlas monthly parquet in `s3://meridian-events-archive/` for older
partitions.

## DynamoDB (`gatekeeper-revoked-jwt-ids`)

- **Point-in-time recovery:** enabled. 35-day window.
- **On-demand backup:** none scheduled — the table is small and losing
  it briefly just means a widened effective revocation window bounded by
  the 60-minute access-token TTL.

## Redis (all three clusters)

- **Backups:** none. Redis is a cache/session store, not a source of
  truth. Losing a Redis cluster forces re-login (sessions) or a brief
  cold cache (Beacon/Portal); it does not lose customer data.
- **AOF / RDB snapshots:** disabled.
- **Justification:** ADR-0044 — Redis is not the source of truth for
  anything the business cares about. Anything durable belongs in
  Postgres or DynamoDB.

## S3 buckets holding data

- `meridian-events-archive`: versioning enabled, cross-region replication
  to `us-east-1`, lifecycle to Glacier after 90 days.
- `meridian-exports`: versioning enabled, no cross-region.
- `meridian-clickhouse-backups`: versioning enabled, no cross-region
  (backups can be regenerated).

## Restore drills

We run a **quarterly restore drill**. The point is not to prove the tool
works — it's to prove that the on-call engineer, using only the current
runbook, can restore against a real dataset in the target RTO.

- **Last drill:** 2026-05-20. Restored `meridian_app` from a snapshot
  taken 12h prior, into an isolated VPC, and successfully brought Portal
  up against it in read-only mode. Ticket: **ENG-4412**. Total time to
  serve a query: 43 min (under the 60-min RTO).
- **Next drill:** 2026-08-25 (scheduled). Owner: SRE on-call rotation.

Findings from each drill get filed as SRE tickets and, where they
change the runbook, land in `runbooks/restore-*.md`.

## Related

- `database/postgres-schema.md`
- `database/clickhouse-schema.md`
- `database/redis-usage.md`
- `database/dynamodb-usage.md`
