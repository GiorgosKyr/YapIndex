---
title: Pricing Tiers
category: product
author: Sam Whitfield
team: Product
created: 2025-01-14
updated: 2026-06-10
status: current
version: 4.2
---

# Meridian Pricing Tiers

This is the current published tier structure. Public pricing page:
`meridiandata.io/pricing`. Sales-facing rate card lives in the CRM.

All plans meter on **MTEs — monthly tracked events**. An MTE is one
enriched event landing in ClickHouse after de-duplication (see the
FAQ at `docs.meridiandata.io/billing/mtes` for the exact definition).
Counters are maintained in Postgres (`usage_counters` table on the
Ledger DB) — as of ADR-0044, Postgres is the source of truth, not
Redis. Nightly reconciliation runs off ClickHouse for correctness.

## Tiers

### Starter — $99/mo

- Up to **250,000 MTEs** included; $0.50 per additional 1,000.
- Up to **5 seats**.
- **1 workspace.**
- Standard reports: dashboards, funnels, cohorts (basic).
- API access: read-only via v3.
- Data retention: 25 months (all plans).
- Support: email, 24-hour business-hours response.
- Not available: SSO, SCIM, custom retention, priority support, SLA.

Best for: single-brand DTC, evaluation, small teams. Kettle & Kiln
started here in 2019.

### Growth — $499/mo

- Up to **2,500,000 MTEs** included; $0.30 per additional 1,000.
- Up to **20 seats**.
- **Up to 3 workspaces.**
- Everything in Starter, plus:
  - Full cohort analysis (custom cohorts, RFM segments).
  - Basic attribution (first-touch, last-touch — from v1;
    see `product/prd-legacy-attribution-v1.md`).
  - Webhooks (via Relay) — up to 5 endpoints.
  - Custom event schemas via Cartograph.
- Support: email, 8-hour business-hours response.
- Not available: SSO, SCIM, SLA.

### Scale — $1,999/mo

- Up to **15,000,000 MTEs** included; $0.15 per additional 1,000.
- Up to **50 seats**.
- **Unlimited workspaces.**
- Everything in Growth, plus:
  - Multi-touch attribution (Attribution v2, once shipped Q4 2026 —
    see `product/prd-attribution-v2.md`).
  - Unlimited Relay webhooks.
  - Lighthouse alerts (in-product metric alerting).
  - Nightly warehouse exports via Atlas (S3, up to 5TB/mo).
  - Higher rate limits on all API endpoints (see
    `api/api-rate-limiting.md`).
- Support: 4-hour response, 24/5 (Mon-Fri, follow-the-sun via London hub).
- Not available: named CSM, SSO, SCIM.

### Enterprise — custom pricing

- Custom MTE volumes (typical floor: 50M/mo).
- Unlimited seats and workspaces.
- Everything in Scale, plus:
  - **SSO** (SAML via WorkOS; Okta, Azure AD, Google Workspace).
  - **SCIM** provisioning (Q4 2026 — see
    `product/prd-scim-provisioning.md`).
  - Named Customer Success Manager.
  - Written SLA: 99.9% for Beacon, 99.95% for Aurora ingest.
    Details in the MSA; see `docs.meridiandata.io/legal/sla`.
  - Slack Connect channel with support and CSM.
  - Custom retention beyond 25 months (up to 60 months).
  - EU region option (Q4 2026 — see `product/prd-eu-region.md`).
  - Dedicated onboarding via Compass with white-glove data import.
- Support: 1-hour response, 24/7. See `support/customer-tiers.md`.

## Metering & overages

Usage counters increment in the enrichment stage (Pulse) and are
flushed to Postgres every 30s in a batched write. Ledger reads
`usage_counters` on the invoice-generation job (runs 03:00 UTC daily
for daily accrual, monthly bill on the workspace's anniversary).

Overages are billed at the per-1,000 rate above and appear as a
line item on the next invoice.

## Discounts

- **Annual pre-pay:** 15% off list.
- **Multi-year (2y+):** 20% off, custom.
- Non-profits and pre-seed startups: contact sales — case by case.

## Sunset / legacy plans

- Old "Team" plan ($299/mo, pre-2024) — grandfathered until 2027-01-01.
  Sales should not be selling it.
- Old "Starter Lite" (from 2020) — 12 customers remaining, migrating
  case by case.

For questions, `pricing@meridiandata.io`.
