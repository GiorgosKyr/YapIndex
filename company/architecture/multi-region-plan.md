---
title: Multi-Region Plan (EU / Frankfurt)
category: architecture
author: Priya Ramanathan
team: Platform
created: 2026-03-11
updated: 2026-08-04
status: draft
version: 0.4
---

# Multi-Region Plan — EU / Frankfurt

Draft plan for the Q3 2026 EU region buildout. Target region:
`eu-central-1` (Frankfurt). Not GA yet; this doc is the shared plan
that Platform, Ingest, Data, Security, and Product Eng are working
from. See `product/prd-eu-region.md` for the product/customer view.

**Status:** draft. Numbers below are the current design intent, not
committed SLOs.

## Goals

1. **Data residency for EU customers.** Event data for EU-flagged
   workspaces stays in `eu-central-1` for storage and query.
2. **Regional write locality.** EU customer SDKs write to an EU-region
   Aurora, not us-west-2.
3. **No product regression** — same dashboards, same API surface, same
   Portal.
4. **Billing stays single-region for now.** Ledger and Stripe
   integration remain in us-west-2. GDPR/DPA impact reviewed with
   Security; separate ADR to follow if we ever move it.

Explicit non-goals for Q3:

- Cross-region failover of Aurora (we're not building us-west-2 → EU
  hot failover; regional isolation is on purpose).
- Multi-master Postgres. See "Postgres" below.

## Topology

Region model: **active-active for the ingest and read paths;
single-region for billing and secrets.**

### Ingest — active-active per region

- **Aurora** deployed in both us-west-2 and eu-central-1. EU customer
  SDKs point at `events.eu.meridiandata.io` (CloudFront + regional
  ALB). Writes to the local Kafka.
- **Kafka (MSK)** — a separate MSK cluster in eu-central-1. Topic
  layout mirrors us-west-2 (see `event-pipeline.md`): `events.raw`,
  `events.enriched`, `events.dlq`.
- **Pulse** in-region, consuming the local Kafka and writing to the
  local ClickHouse. No cross-region hop for event data.
- **Cartograph** in-region (schemas replicated from us-west-2 Postgres
  via logical replication, see below).

### Storage — regional ClickHouse clusters

- New ClickHouse cluster in eu-central-1. Sized initially at 3 nodes;
  scale to match us-west-2 (6 nodes) once EU volume warrants it.
- No cross-region ClickHouse replication. If we ever need
  "global-view" analytics we'll build a federated query layer, not a
  replicated table.

### Postgres — single primary in us-west-2

- The Postgres primary stays in `us-west-2` (`meridian-prod-primary`).
- **Logical replication** to a Postgres replica in `eu-central-1` for
  a **subset of tables** — the ones that in-region services must read
  synchronously on the ingest path:
  - `workspaces`
  - `workspace_write_keys`
  - `event_schemas`
  - `cohort_definitions`
  - `webhook_subscriptions`
- Writes to those tables always land in us-west-2 (portal + admin
  CRUD stay us-west-2 routed). EU services are read-only against the
  local replica.
- Explicitly **not** replicated: `users`, `sessions`, billing tables.
  These stay us-west-2-only; the Portal in EU calls back to us-west-2
  for auth and billing.

### Ledger — stays in us-west-2

Billing single-region for now. This is a scope decision, not a
capability decision. Rationale:

- Stripe account is single-region; a second EU Stripe account
  materially reshapes tax handling.
- Metered billing reads from ClickHouse — with regional ClickHouse
  clusters we'd need to aggregate across regions.
- No customer requirement yet for EU-hosted invoicing.

Ledger will call the EU ClickHouse for EU-workspace MTE counts over
the private mesh; the Ledger deployment itself stays in `us-west-2`.

### Portal + Beacon — deployed in both regions

- Portal deployed in eu-central-1; region routing at CloudFront based
  on the workspace's residency flag (set at signup in Compass).
- Beacon deployed in eu-central-1; queries the local ClickHouse.
- Gatekeeper is deployed in both regions; it authenticates against
  the us-west-2 Postgres for the user tables (short-lived token cache
  in-region).

## Network

- New VPC in eu-central-1: `10.60.0.0/16` (`prod-eu`).
- VPC peering us-west-2 ↔ eu-central-1 for Postgres logical
  replication, cross-region Gatekeeper reads, and Ledger's ClickHouse
  reads.
- No public traffic between regions; all cross-region hops go over
  the private mesh.

## Rollout

- **T0 (Q3 2026 in progress):** infra buildout, Postgres logical
  replication live, EU Kafka + ClickHouse standing up in staging.
- **T1:** first design-partner EU workspace, opted-in, low volume.
- **T2 (target Q4 2026):** GA. Data-residency toggle exposed in
  Portal via `settings/data-region`. Compass region routing live.

Open items — tracked in `architecture/open-questions-eu.md`:

- Cross-region latency budget for Gatekeeper token minting.
- DR story for the EU region (mirror to another EU region? backups
  only?).
- Cost model — the FinOps note is being drafted by Marcus.
