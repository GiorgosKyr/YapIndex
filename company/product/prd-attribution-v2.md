---
title: Multi-Touch Attribution v2
category: prd
author: Sam Whitfield
team: Product
created: 2026-06-14
updated: 2026-08-12
status: draft
version: 0.7
---

# PRD: Multi-Touch Attribution v2

**Target ship:** Q4 2026
**Owner:** Sam Whitfield (Product), eng lead TBD (Product Eng)
**Related:** `product/prd-legacy-attribution-v1.md` (predecessor, archived)

## Problem

Meridian's current attribution feature — shipped 2024-Q4 — supports only
single-touch models (first-touch or last-touch). Customers on the Growth
and Scale tiers have consistently asked for multi-touch models in QBRs and
in-app feedback: 41 named requests over the last 12 months, second-most
requested feature after EU data residency.

Single-touch attribution misrepresents the customer journey for e-commerce
brands with long consideration windows (Nordwind Cycles is the poster
child — median 14-day time-to-purchase). Growth marketers can't defend
ad spend allocation to their exec teams using our numbers, and several
Scale accounts have started dual-running Rockerbox alongside Meridian,
which is a churn signal.

## Goals

- Ship linear, time-decay, and custom (user-weighted) attribution models.
- Expose results through a new query endpoint: `POST /v3/attribution/queries`.
  Request body specifies model, lookback window, conversion event, and
  channel dimension.
- Surface results in Portal under the existing Reports section as a new
  "Attribution" report type (not a new nav item).
- Match the existing v1 latency SLO: p95 < 4s for queries over 90 days
  of data, per workspace.
- Backfill: last 25 months of data become queryable at launch (matches
  standard retention).

## Non-goals

- Cross-device stitching (deferred — needs a separate identity project).
- Incrementality testing / holdouts.
- Attribution for offline conversions uploaded via CSV.
- Model transparency ("why did this touch get X% credit") beyond the
  documented formulas — no explainability UI in v1 of v2.

## Proposed solution

Attribution queries are computed by Beacon against a new ClickHouse
materialized view `mv_touch_paths_v2` that Pulse populates in near-real-time
(the touch-path assembly runs in the enrichment stage). Beacon-Aggregator
caches per-workspace results with a 15-minute TTL — parity with existing
report caching behavior.

Portal renders three linked visualizations: a channel-contribution bar
chart, a Sankey of top touch paths, and a comparison table across models
(so a marketer can see "last-touch says $X, linear says $Y, time-decay
says $Z" in one view).

Custom models are defined via a simple JSON weight vector supplied in
the API call; Portal exposes a preset editor. Weights must sum to 1.0
(±0.001); we reject otherwise with `ATTRIBUTION_INVALID_WEIGHTS`.

Docs will live at `docs.meridiandata.io/reports/attribution` and
`docs.meridiandata.io/api/attribution`.

## Risks

- **Beacon-Aggregator schema changes.** The rollup cache today assumes a
  fact table with one row per event. Multi-touch paths need a compound key.
  Elena's team estimates 3 weeks for the schema migration; we are BLOCKED
  on that landing before we can start Beacon integration work. Ticket
  PROD-2141.
- **ClickHouse memory.** Touch-path assembly is memory-hungry. Data team
  has flagged this as a re-run risk of INC-2026-02-03 (Q4 export OOM)
  unless we cap path length at 25 touches. Tentative decision: cap.
- **v3 API only.** Customers still on v2 (EOL 2026-11-01) will not get
  this feature. Support should have a talk track ready.

## Open questions

- Should the "custom" model be per-workspace or per-report? Sam leans per-workspace.
- Do we surface attribution in the existing Funnels report, or keep it
  entirely separate? Elena wants separate; design has both mocks.
- Pricing: is attribution a Scale+ feature, or Growth+? See
  `product/pricing-tiers.md` — not yet decided.
- Naming: "Attribution v2" is the internal name. External name TBD;
  marketing has proposed "Journey Attribution".
