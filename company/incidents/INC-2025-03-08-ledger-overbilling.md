---
title: "INC-2025-03-08: Ledger overbilling from stale Redis usage counters"
category: incident
author: Tomás Herrera
team: Growth Eng
created: 2025-03-08
updated: 2025-03-09
status: resolved
version: 1.3
---

# INC-2025-03-08 — Ledger overbilling (Redis eviction + rebuild bug)

- **Severity:** SEV-1
- **Status:** Resolved
- **Detected:** 2025-03-08 09:12 PT via customer email + Datadog anomaly
  monitor `dd:monitor/41277` on `ledger.invoice.total_amount_delta_pct`
- **Resolved:** 2025-03-08 22:40 PT (all customers notified, refunds queued)
- **PagerDuty:** PD-INC-D08815
- **Slack channel:** `#inc-2025-03-08`
- **Responders:** Tomás Herrera (IC), Ravi Patel, Priya Ramanathan
  (Redis operator context), Jae-won Park (ClickHouse recompute), Dara
  Okonkwo (audit), Lin Zhao (customer comms)

## Summary

Overnight (~02:00 – 03:30 PT on Mar 8), the `meridian-cache-prod` Redis
cluster experienced memory pressure and evicted a large fraction of the
`usage_counter:*` key space under its `allkeys-lru` policy. Ledger's
nightly recovery cron (`recompute_usage_counters` at 04:00 PT) detected
missing counters and rebuilt them by querying ClickHouse — which is
correct. However, a bug in `ledger/jobs/recompute_usage.py` caused the
rebuilt counter values to be **added to** existing (already-billed)
`billed_amount_ytd` totals in Postgres, rather than **replaced**. The
next billing tick at 06:00 PT then generated invoices using the
double-counted totals.

Invoices had already been sent to Stripe and, for customers on auto-pay,
charged, by the time the anomaly monitor fired at 09:12 PT.

## Impact

- **Customers affected:** 41 workspaces on the Growth and Scale tiers.
- **Total incorrect charges:** $61,842.19.
- **Refunds:** All 41 refunded within 24 hours via Stripe.
- **Trust impact:** Two customers (both on Growth tier) subsequently
  churned citing this incident.

## Timeline (PT)

- **02:04** — Redis `meridian-cache-prod` `used_memory` hits 92% of
  `maxmemory`. `allkeys-lru` begins evicting keys.
- **02:04 – 03:32** — ~4.1M keys evicted. `usage_counter:*` heavily
  affected (large keyspace, TTL varied).
- **04:00** — `recompute_usage_counters` cron starts. Detects missing
  counters. Queries ClickHouse for correct values. Writes to Redis
  (correct) AND updates Postgres `workspace_billing.billed_amount_ytd`
  by **`SET billed_amount_ytd = billed_amount_ytd + :computed`**
  (WRONG; should have been `SET billed_amount_ytd = :computed`).
- **06:00** — Nightly billing tick runs. Invoices generated from
  Postgres. Overbilled totals sent to Stripe.
- **06:30** — First auto-pay charges succeed at Stripe.
- **08:47** — First customer email arrives: "Why is my invoice 3x?"
- **09:12** — `dd:monitor/41277` fires SEV-2 on
  `ledger.invoice.total_amount_delta_pct` — YTD amount delta was
  190%+ month-over-month for 41 workspaces.
- **09:19** — Tomás declares SEV-1. Ledger billing tick paused
  immediately (`billing.enabled=false` in LaunchDarkly).
- **10:40** — Root cause identified in `recompute_usage_counters`.
- **11:15** — Postgres `workspace_billing` restored from the pre-cron
  snapshot (04:00 PT) — clean baseline. Re-run of counter recompute
  from ClickHouse with corrected `SET` (not `+=`) logic.
- **12:30** — Refund script drafted, reviewed by Dara.
- **14:00 – 18:00** — Refunds processed in batches.
- **19:00 – 22:00** — Lin sends personalized emails to all 41 affected
  workspaces from `billing@meridiandata.io`.
- **22:40** — Incident closed. Billing tick re-enabled after refund
  reconciliation confirmed clean.

## Mitigation

1. Billing tick paused via feature flag.
2. Postgres `workspace_billing` restored from 04:00 PT snapshot.
3. `recompute_usage_counters` corrected to overwrite, not add.
4. All 41 customers refunded and notified.

## Follow-up

Full postmortem: `postmortems/2025-03-08-ledger-overbilling.md`.
This incident drove **ADR-0044** (`adrs/0044-usage-counters-source-of-truth.md`)
— usage counters are now authoritative in Postgres, recomputable from
ClickHouse, and Redis is cache-only.
