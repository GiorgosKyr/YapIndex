---
title: "PRD — Attribution v1 (single-touch)"
category: product
author: Sam Whitfield
team: Product
created: 2024-06-10
updated: 2024-10-28
status: archived
version: 2.3
---

> **ARCHIVED.** This PRD describes Attribution v1, which shipped in
> 2024-Q4. It is retained for historical reference. The **current**
> attribution PRD is `product/prd-attribution-v2.md` (multi-touch).

# PRD: Attribution v1

## Problem

Meridian customers want to know which marketing channel drove a
conversion. Today they can see raw events and cohort membership but have
no first-class attribution report.

## Goals

- Ship a "Sources of Conversions" report in Portal by end of Q4 2024.
- Support two attribution models:
  - **First-touch:** first known channel in the user's history gets the
    credit.
  - **Last-touch:** last channel before conversion gets the credit.
- Configurable conversion event per workspace (defaults to `order.completed`).
- 90-day attribution window (configurable up to 180 days).

## Non-goals

- Multi-touch models (linear, time-decay, U-shaped, data-driven). Deferred
  to a v2.
- Cross-device stitching beyond our existing `user_id`-based join.
- Paid-media integrations (Google Ads, Meta Ads spend import) — separate
  project.

## Proposed solution

- **Server side:** Beacon-Aggregator gains a nightly rollup that
  precomputes attribution for each conversion event per workspace, per
  attribution model. Stored in Postgres table `rollups_attribution_daily`.
- **API:** Beacon exposes `GET /v2/attribution/report` (v3 endpoint added
  post-launch). Query params: `model={first|last}`, `from`, `to`,
  `conversion_event`.
- **UI:** New "Sources" tab in Reports section of Portal. Chart + table.
  CSV export.

## Risks

- Cohort recomputation cost. Mitigated by nightly precompute.
- Customer confusion between first-touch and last-touch results;
  requires clear tooltips.
- Attribution is inherently ambiguous; support docs must explain models.

## Open questions (at time of authoring)

- ~~Do we default to first-touch or last-touch?~~ Resolved 2024-08-04
  meeting: last-touch is default; users can toggle.
- ~~UTM parameter mapping?~~ Resolved: yes, we normalize `utm_source`,
  `utm_medium`, `utm_campaign` into `attribution.channel`,
  `attribution.medium`, `attribution.campaign`.
- ~~Enterprise-only?~~ Resolved: available on Growth and above.

## Launch

Shipped 2024-11-19 to Growth+ customers. Announcement in
`#product-launches`. Support FAQ added.

## Post-mortem (short)

- Adoption above forecast: 38% of eligible workspaces used it in the
  first 30 days.
- Requests for multi-touch started arriving within a week — drove the
  v2 PRD (`product/prd-attribution-v2.md`).

## Related

- Current: `product/prd-attribution-v2.md`
- API endpoint reference: `api/api-v3-reference.md` (attribution section)
- Data model: `database/postgres-schema.md` (`rollups_attribution_daily`)
