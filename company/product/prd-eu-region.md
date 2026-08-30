---
title: EU Region (Frankfurt) — GA
category: prd
author: Sam Whitfield
team: Product
created: 2026-03-02
updated: 2026-07-28
status: in-progress
version: 1.3
---

# PRD: EU Region GA

**Target ship:** Q4 2026 (GA), phased rollout starting late Q3
**Related:** `architecture/multi-region-plan.md`, `product/roadmap-2026.md`

## Problem

We currently operate exclusively out of us-west-2. Data residency in the
EU is now the #1 blocker in enterprise deals — six named opportunities
in the last two quarters (~$1.4M ARR combined) stalled or lost on this,
including two Kettle & Kiln-adjacent DTC brands. GDPR is not the sole
driver; several prospects have internal policies stricter than GDPR that
mandate in-region storage and processing.

The London hub has also been fielding customer complaints about Portal
latency from Central Europe (median TTFB ~380ms). Frankfurt gets us
under 90ms for EU users on top of the compliance win.

## Goals

- Bring `eu-central-1` (Frankfurt) online as a fully independent
  processing region for customer event data.
- Customer chooses region **at workspace creation** (not per-event).
  Once set, it does not move. This is intentional to keep the mental
  model simple — we don't want to explain "some of your data is in the
  EU and some isn't" to support tickets.
- Compass routes new workspace signups to the correct region based on
  the customer's selection during onboarding.
- All customer event storage (ClickHouse), event ingestion (Aurora, Pulse),
  and query serving (Beacon, Beacon-Aggregator) run in-region for EU
  workspaces.
- Publish a data-residency addendum on `docs.meridiandata.io/legal/dpa`.

## Non-goals

- **Ledger** does not move. Billing and subscription data stay in
  us-west-2 for the initial GA. This is a considered trade-off — Stripe
  processing is US-anchored anyway, and moving Ledger doubles the
  compliance surface with minimal customer benefit. We will revisit in
  2027.
- **Gatekeeper** initially runs a single-region model with EU read
  replicas for the session revocation list. Multi-master auth is out
  of scope for this PRD.
- Cross-region workspace migration ("I created it in US, move it to EU").
  Not supported at GA. Customers must recreate.
- Multi-region for a single workspace (i.e. active-active per workspace).
- DR for the EU region — us-east-1 remains US-only DR. EU disaster
  recovery is a Q1 2027 follow-up.

## Proposed solution

- New EKS cluster `meridian-prod-eu` in eu-central-1, provisioned via
  the same Terraform modules as prod-us with a region-parameterized root.
- Regional DNS: `eu.meridiandata.io` for the Portal, `ingest.eu.meridiandata.io`
  for Aurora. Compass sets the correct base URL in the SDK snippets
  emitted during onboarding.
- ClickHouse cluster in-region: 4 nodes at launch, sized to ~30% of
  us-west-2 load headroom.
- Kafka: separate MSK cluster in-region. Topics mirror the US naming
  convention (`events.raw`, `events.enriched`).
- Compass regional routing: a lookup table keyed by workspace UUID
  returned during login redirects Portal to the correct regional origin.
  Gatekeeper JWTs carry a `region` claim.
- Data flow within EU is identical to US; see `architecture/data-flow.md`.

## Risks

- **Split-brain workspaces.** If the region toggle is set incorrectly,
  we could route a customer's events to the wrong region. Mitigation:
  routing is derived from the workspace record in Gatekeeper's Postgres,
  which is single-source. There is no "override" API.
- **Deploy pipeline.** ArgoCD needs region-scoped ApplicationSets.
  Platform team estimates 2 sprints; not fully de-risked.
- **Operational load.** SRE is already stretched. Ben has flagged that
  running two prod regions with the current headcount (4 SREs) is going
  to hurt. Hiring req approved but backfill not yet in seat.

## Open questions

- Do we support region selection via API at workspace creation, or only
  via Portal at first? Leaning Portal-only for GA.
- Support docs will need to explain "EU workspace" behavior clearly.
  Lin's team is drafting.
- What is the exact list of features gated behind US-only at GA
  (Attribution v2? SCIM?) — needs an explicit table before beta.
