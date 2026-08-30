---
title: Postgres Schema — meridian_app
category: database
author: Priya Ramanathan
team: Platform
created: 2024-02-11
updated: 2026-07-14
status: current
version: 4.5
---

# Postgres Schema — `meridian_app`

Meridian's OLTP store is **RDS Postgres 15**, Multi-AZ, in `us-west-2`. The
primary application database is `meridian_app`; a separate `meridian_gatekeeper`
database lives on the same cluster and is owned by Security (see
`security/authentication.md`). Do not add cross-database foreign keys — they
don't exist in Postgres, and even logical references between the two DBs
must go through Gatekeeper's gRPC API.

The instance is `db.r6g.4xlarge`, Multi-AZ with a synchronous standby in a
different AZ. Automated backups are documented in
`database/database-backup-policy.md`.

## Owning teams

Most tables are owned by Product Eng (Elena Vasquez's team). Billing tables
(`subscriptions`, `invoices`, `processed_stripe_events`, `usage_counters`) are
owned by Growth Eng (Tomás Herrera's team) — the Ledger service is the only
writer. Note Ledger internally refers to a workspace as an "account", but the
underlying FK column is always `workspace_id`.

## Key tables

| Table | Purpose | Notes |
|---|---|---|
| `workspaces` | One row per customer workspace (aka organization, tenant). | UUID PK. Soft-delete via `deleted_at`. |
| `users` | Person records. | Email unique, case-insensitive. |
| `workspace_members` | Join table (user_id, workspace_id, role). | Roles enforced by Gatekeeper — see `security/authorization.md`. |
| `api_write_keys` | Ingest write keys per workspace (used by Aurora). | `key_prefix` stored plaintext, `key_hash` bcrypt. |
| `schemas` | Cartograph-managed event schema definitions. | Versioned; `is_active` at most one per (workspace, event_name). |
| `properties` | Per-schema property/dimension definitions. | Called "tag" in some Cartograph code. |
| `subscriptions` | Ledger — one row per active Stripe subscription. | FK to `workspaces`. |
| `invoices` | Ledger — cached invoice metadata mirrored from Stripe. | Stripe is the source of truth for amounts. |
| `usage_counters` | MTE (monthly tracked event) counters per (workspace, period). | Moved here from Redis on 2025-03-19, see ADR-0044 and INC-2025-03-08. |
| `processed_stripe_events` | Dedup table for incoming Stripe webhooks. | Added after INC-2024-11-14. |
| `alerts` | Lighthouse — user-configured metric alerts. | Runs on Beacon-Aggregator rollups. |
| `reports` | Portal — saved dashboards/reports/views. | JSONB `spec` column. |
| `webhooks` | Relay — customer webhook subscriptions. | |
| `webhook_deliveries` | Relay — per-delivery attempt log. | Partitioned by day; 30-day retention. |

## DDL snippets

### `usage_counters`

Postgres has been authoritative for MTE counters since March 2025. See
ADR-0044 for the rationale. Ledger updates this table transactionally
alongside `processed_stripe_events` when reconciling.

```sql
CREATE TABLE usage_counters (
    workspace_id     UUID        NOT NULL REFERENCES workspaces(id),
    period_start     DATE        NOT NULL,   -- first day of billing month, UTC
    metric           TEXT        NOT NULL,   -- 'mte', 'mte_enriched', ...
    count            BIGINT      NOT NULL DEFAULT 0,
    last_updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, period_start, metric)
);

CREATE INDEX usage_counters_period_idx
    ON usage_counters (period_start, metric);
```

Writers use `INSERT ... ON CONFLICT DO UPDATE SET count = usage_counters.count + EXCLUDED.count`.
Readers (Portal billing UI) should query with `SELECT ... FOR SHARE` if part of
a checkout flow, otherwise dirty reads are fine.

### `processed_stripe_events`

Added after the November 2024 double-charge incident (INC-2024-11-14). Every
Stripe webhook handler MUST insert here inside the same transaction as the
side effect. The unique constraint is the dedup mechanism.

```sql
CREATE TABLE processed_stripe_events (
    event_id      TEXT        PRIMARY KEY,   -- Stripe evt_...
    event_type    TEXT        NOT NULL,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_hash  BYTEA       NOT NULL
);

CREATE INDEX processed_stripe_events_received_idx
    ON processed_stripe_events (received_at);
```

A daily job (Atlas) prunes rows older than 90 days.

## Access patterns

- Direct connections from services go through PgBouncer (transaction pooling).
- Read replicas: two async replicas, used by Beacon for reporting-style
  lookups and by Atlas for nightly extracts.
- Long-running analytical queries do NOT go here — use ClickHouse
  (`database/clickhouse-schema.md`).

## Migrations

Alembic (Python services) and `golang-migrate` (Aurora, Gatekeeper).
Migration PRs require a Platform reviewer. Zero-downtime migrations only —
no `DROP COLUMN` on hot paths without a two-deploy expand/contract.
