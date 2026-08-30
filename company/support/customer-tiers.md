---
title: Customer Support Tiers and SLAs
category: support
author: Lin Zhao
team: Support
created: 2025-01-14
updated: 2026-06-15
status: current
version: 2.4
---

# Customer Support Tiers and SLAs

Support response times and channels by pricing tier. For internal
escalation flow see `support/escalation-policy.md`. Pricing details
in `product/pricing-tiers.md`.

## Response-time SLAs (first response)

| Plan | S1 | S2 | S3 | S4 | Hours |
|------|----|----|----|----|-------|
| Starter | 24h | 24h | 48h | best effort | Business (Mon–Fri, 9–5 PT) |
| Growth | 8h | 12h | 24h | best effort | Business |
| Scale | 4h | 8h | 12h | best effort | 24 × 5 (Mon–Fri) |
| Enterprise | 1h | 2h | 8h | best effort | 24 × 7 |

*"Business hours" = Mon–Fri, 09:00–17:00 Pacific, excluding US federal
holidays. "24×5" = 24-hour coverage Mon–Fri. "24×7" = around-the-clock.*

## Channels

| Plan | Email | In-app chat | Slack Connect | Named CSM | Video call |
|------|-------|-------------|---------------|-----------|-----------|
| Starter | ✅ | — | — | — | — |
| Growth | ✅ | ✅ | — | — | on request |
| Scale | ✅ | ✅ | on request | shared pool | included |
| Enterprise | ✅ | ✅ | ✅ | ✅ dedicated | ✅ scheduled |

## Uptime SLAs (from MSA)

| Plan | Monthly uptime commitment | Credits |
|------|---------------------------|---------|
| Starter, Growth | None (best effort) | — |
| Scale | 99.9% | 10% credit if <99.9%, 25% if <99.0% |
| Enterprise | 99.95% | Custom in MSA |

The scope of "uptime" is the ingest API and read API. Portal availability
and dashboard freshness are tracked but not in the SLA (yet — Product is
scoping this for 2027).

## Data residency

- All plans today are served from `us-west-2`.
- EU region (Frankfurt) is a **Q4 2026 target** for Enterprise (and
  Scale on request). Contact your CSM for early access.

## Historical incidents that changed policy

- **[INC-2024-11-14](../incidents/INC-2024-11-14-duplicate-charges.md)**
  (duplicate charges) — Enterprise S1 response time tightened from 2h
  to 1h. Billing anomalies always S1.
- **[INC-2025-06-12](../incidents/INC-2025-06-12-eks-upgrade.md)**
  (EKS upgrade) — Scale plan uptime credits threshold changed from
  99.5% to 99.9%.

## Ownership

- Policy owner: Lin Zhao (Head of Support).
- SLA compliance reporting: monthly, presented at exec review.
- Contract-level exceptions: negotiated per-deal by Sales + CSM,
  documented in Salesforce.
