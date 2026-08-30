---
title: Product Roadmap — H2 2026 & Q1 2027
category: product
author: Sam Whitfield
team: Product
created: 2026-01-08
updated: 2026-08-20
status: current
version: 8
---

# Roadmap — as of Aug 2026

Rolling 3-quarter view. Priorities set at the Aug offsite. Confidence
labels: **committed** (dated externally, we owe it), **planned**
(scoped, not dated externally), **exploratory** (still in shaping).

Owners are eng lead + PM. Nadia and Marcus signed off on this version.

## Q3 2026 (current, in flight)

### EU region — Frankfurt (committed)

Infra buildout underway. GA planned for Q4 (see below). By end of Q3
we want the region reachable internally, all services deployed, and
first external beta customers in the workspace-selector UI.

Owner: Priya (Platform), Sam W (Product).
PRD: `product/prd-eu-region.md`.

### Beacon-Aggregator schema v2 (planned)

Schema migration for multi-touch attribution rollups. Blocker for
Attribution v2. Elena's team; 3 sprints.

### v2 API sunset comms (committed)

v2 EOL is 2026-11-01 (extended once from 2026-05-20). Support and
Marketing running the customer notification cadence: T-90, T-30, T-7.
See `api/v2-deprecation-plan.md`.

## Q4 2026

### EU region — GA (committed)

Full data residency. Customer chooses at workspace creation, Compass
routes correctly. Ledger stays in us-west-2 for GA (explicit trade-off).
PRD: `product/prd-eu-region.md`.

### SCIM 2.0 provisioning (committed)

For Enterprise SSO customers. Depends on Gatekeeper user-model
changes landing early in the quarter. Okta + Azure AD validated at GA.
PRD: `product/prd-scim-provisioning.md`.

### Attribution v2 — multi-touch (committed)

Linear, time-decay, and custom-weight attribution models. New endpoint
`POST /v3/attribution/queries` and a new Attribution report type in
Portal. Scale-tier and above.
PRD: `product/prd-attribution-v2.md`.
Predecessor (archived): `product/prd-legacy-attribution-v1.md`.

### Lighthouse quiet hours (planned)

Small quality-of-life feature — alert suppression during customer-defined
maintenance windows. Elena's team, one sprint. Not a marketing beat.

## Q1 2027

### ClickHouse Keeper migration (planned)

Move off ZooKeeper as ClickHouse's coordination backend. Jae-won's
team leading. Motivated by ops toil and a stale ZK 3.7 CVE we've been
patching around. Zero customer-visible change if we do it right; but
non-trivial. Expected to land end of Q1 or slip to early Q2.

### ML anomaly detection (planned)

Insights team's first customer-facing feature: automated anomaly
detection on customer-defined metrics. Uses a lightweight forecasting
model (Prophet-like) plus a rules layer. Gated behind LaunchDarkly
flag `ml-anomaly-beta` at first, then Scale+ GA.

Owner: Priya (interim, ML/Insights) + Sam W. Concept design in
`meetings/2026-07-11-ml-shaping.md`.

### Retention self-service (exploratory)

Enterprise customers currently negotiate retention (up to 60 months)
via CSM. We want a Portal self-service toggle for custom retention.
Blocked on Atlas being able to do partial-retention exports; Jae-won
has flagged this as a bigger data-team lift than it looks.

## Q2 2027 (peeking ahead — subject to change)

- **Snowflake connector** (reverse ETL) — evaluated in 2022 and rejected
  as a warehouse, but a customer-facing connector is very different and
  now well-motivated by our Enterprise book. Champion: Jae-won.
- **Cross-device identity stitching.** Blocker for eventually revisiting
  attribution scoping.
- **EU region DR.** Currently EU has no DR — Q2 target for warm-standby.

## What we're explicitly NOT doing

Kept here because we get asked:

- Snowflake / BigQuery / Databricks as a customer-facing warehouse
  replacement for our ClickHouse. Not happening — see ADR-0014.
- Mobile SDKs beyond the JS web SDK and the server-side Python/Go/Ruby
  SDKs we ship today. iOS/Android are not a priority through H1 2027.
- On-prem / self-hosted deployments. Repeatedly asked; consistently
  declined by Nadia.
- A CDP-style identity graph. Overlaps with cross-device (above) but
  the full CDP framing is a bigger commitment than we want.

## Change log

- v8 (2026-08-20): moved SCIM from "planned" to "committed" for Q4
  after leadership review. Added ClickHouse Keeper explicitly.
- v7 (2026-06-30): added EU DR to Q2 2027.
- v6 (2026-05-05): removed on-prem exploration from Q1 2027 (see above).
