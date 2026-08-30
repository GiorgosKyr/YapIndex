---
title: "Postmortem: Ledger overbilling from stale Redis (2025-03-08)"
category: postmortem
author: Tomás Herrera
team: Growth Eng
created: 2025-03-24
updated: 2025-04-11
status: current
version: 1.2
---

# Postmortem — 2025-03-08: Ledger overbilling from stale Redis

> Related incident: `incidents/INC-2025-03-08-ledger-overbilling.md`
> Related ADR: `adrs/0044-usage-counters-source-of-truth.md`
> Related meeting: `meetings/2025-03-10-ledger-incident-review.md`
> Blameless. Reviewed and endorsed by Ravi, Dara, Tomás, Elena.

## Summary

On 2025-03-08, the nightly Ledger billing tick generated invoices
using usage totals that had been silently double-counted by an
overnight recovery job. 41 customer workspaces were overbilled by a
total of $61,842.19. All charges were refunded within 24 hours; two
customers later churned citing this incident. The root cause was a
compound failure: Redis was authoritative for usage counters, Redis
experienced memory pressure and evicted keys, and the recovery job
that rebuilt those counters from ClickHouse **added** its computed
values to the running totals in Postgres instead of **replacing**
them.

This postmortem was the primary driver of ADR-0044, which forbids
Redis as source of truth for billable state.

## Impact

- Workspaces overbilled: 41 (Growth and Scale tiers).
- Total incorrect charge amount: $61,842.19.
- Refund latency: all refunded within 24h.
- Customer churn attributable: 2 workspaces (~$28K ARR).
- Ledger billing tick paused for ~13 hours during recovery.
- Datadog anomaly monitor `dd:monitor/41277` caught the invoice
  delta; it did NOT catch the counter double-count in Redis before
  invoicing.

## Timeline (PT)

- **Mar 8 02:04 – 03:32** — Redis `meridian-cache-prod` `used_memory`
  hits 92% of `maxmemory` (12GB / 13GB). `allkeys-lru` eviction
  policy begins removing keys. Approximately 4.1M keys evicted,
  including a large fraction of `usage_counter:*`.
- **04:00** — `ledger.jobs.recompute_usage_counters` cron runs
  (nightly). Detects missing `usage_counter:*` keys. Queries
  ClickHouse for correct MTD event counts per workspace. Writes
  correct value to Redis. **Also updates Postgres
  `workspace_billing.billed_amount_ytd` with `SET billed_amount_ytd
  = billed_amount_ytd + :computed` instead of `SET billed_amount_ytd
  = :computed`.**
- **06:00** — Nightly billing tick runs. Reads inflated
  `billed_amount_ytd` from Postgres. Generates monthly invoices
  using the delta from previous month's `billed_amount_ytd`. For
  workspaces whose counters had been rebuilt, the invoice reflects
  roughly 2x actual usage.
- **06:30** — Auto-pay charges begin succeeding at Stripe.
- **08:47** — First customer email.
- **09:12** — `dd:monitor/41277` fires SEV-2 on invoice-total delta.
- **09:19** — Tomás declares SEV-1. Billing tick paused via
  LaunchDarkly (`billing.enabled=false`).
- **10:40** — Root cause identified in `recompute_usage_counters`.
- **11:15** — Postgres `workspace_billing` restored from the
  automated 04:00 PT snapshot. Counter recompute re-run with
  corrected logic.
- **12:30 – 18:00** — Refunds scripted, reviewed by Dara,
  processed in batches.
- **19:00 – 22:00** — Lin sends 41 personalized apology emails.
- **22:40** — Incident closed.

## Root cause

The direct code defect: `ledger/jobs/recompute_usage_counters.py`
line 187 used `+=` semantics when persisting recomputed totals to
Postgres. This was intended to be idempotent-safe assuming Redis
was source of truth (the Postgres row was thought to be a
"materialization for billing"), but Redis had evicted the counters,
so the "already-billed" and "to-be-billed" concepts collided.

The deeper design defect: **Redis was authoritative for usage
counters.** Postgres held only a nightly-flushed materialization
used at billing time. There was no durable authoritative store for
"how much has this workspace used this month". When Redis lost the
data, we had no correct place to rebuild from without also
recomputing what had already been billed — and the recompute
conflated the two.

## Contributing factors

- **`maxmemory` and eviction policy on `meridian-cache-prod` were
  the ElastiCache defaults.** No one had explicitly chosen
  `allkeys-lru` for billing-critical state — it was inherited from
  when the cluster was used for session caching only (see
  `adrs/0001-*.md` for the origin story).
- **Redis was quietly load-crept.** The cluster had grown from
  serving sessions (2020), to query result caching (2022), to rate
  limiting (2023), to usage counters (2024). No single owner had
  audited what was on it or set memory budgets per use case.
- **The recompute cron had no dry-run mode.** Its first run in prod
  was its first meaningful test in prod, because the eviction
  scenario had never been exercised in staging.
- **The Datadog anomaly monitor was on invoice output, not usage
  input.** By the time it fired, invoices had already been sent.
- **`billed_amount_ytd` had no immutable-record equivalent.** There
  was no `invoice_line_items` table with per-charge history at the
  MTE level, so the recompute couldn't reason about "what did we
  already bill for".

## What went well

- Once escalated, the billing tick was paused within 7 minutes.
  Feature-flag kill switch worked as designed.
- Postgres snapshot from 04:00 PT was available and restorable.
  This is the reason the recovery was hours, not days.
- Dara reviewed the refund script line-by-line before execution.
  This is exactly the security-review process we wanted from her
  role.
- Cross-team collaboration (Growth Eng, Data, Platform, Security,
  Support) was calm and effective. `#inc-2025-03-08` was the
  single source of truth throughout.

## What went poorly

- We were bitten by a Redis-as-source-of-truth pattern we had
  already been warned about by INC-2024-11-14 (where the hotfix
  used Redis for dedupe). We did not internalize the lesson.
- The eviction policy on `meridian-cache-prod` was wrong for the
  data on it, and no one had ever noticed.
- The recompute cron was written defensively for the "counters are
  low" case but not for "counters were evicted and Postgres already
  reflects billed state".
- Detection was via customer email, not our own monitoring — again.
- The two churned customers were both mid-market accounts on
  Growth. This is precisely the segment we most need to retain.

## Action items

| # | Owner | Description | Status | Due |
|---|-------|-------------|--------|-----|
| 1 | Tomás / Ravi | **Usage counters authoritative in Postgres, recomputable from ClickHouse, Redis is cache-only.** Formalized as `adrs/0044-usage-counters-source-of-truth.md`. Implementation: `workspace_usage` table, per-MTE-batch inserts, no delete/update. | done | 2025-04-30 (ADR), 2025-05-28 (impl) |
| 2 | Priya | Audit `meridian-cache-prod` contents. Split billing-critical caches to a separate ElastiCache cluster (`meridian-cache-billing-prod`) with `maxmemory-policy noeviction` and monitoring on eviction count. | done | 2025-05-15 |
| 3 | Elena | Datadog monitor on `ledger.usage_counter.delta_pct` per workspace, hourly. Fires if delta > 200% vs 7-day baseline. `dd:monitor/42910`. | done | 2025-04-08 |
| 4 | Tomás | Recompute job: dry-run mode required; must be manually approved for prod runs; refuses to run if delta > threshold without `--force`. | done | 2025-04-22 |
| 5 | Jae-won | `workspace_usage_daily` materialized view in ClickHouse to make recompute cheap and idempotent. | done | 2025-05-05 |
| 6 | Sam / Lin | Customer-facing "billing accuracy" commitment published in Trust Center; refund policy formalized. | done | 2025-06-03 |
| 7 | Tomás | **Postmortem-of-the-postmortem** at 30 days: confirm all AIs on track, review any new incidents pointing at the same root pattern. | done | 2025-04-11 (confirmed all 6 above on track or shipped) |

## References

- `adrs/0044-usage-counters-source-of-truth.md` — the durable
  outcome of this incident.
- `meetings/2025-03-10-ledger-incident-review.md` — the working
  meeting held two days after the incident with Ravi, Tomás,
  Elena, Priya, Dara, Lin, and Sam. Drove the ADR outline.
- `backend/ledger-service.md` — rewritten to reflect the new
  authoritative-in-Postgres model.
- Related prior incident: `incidents/INC-2024-11-14-duplicate-charges.md`
  — same underlying "Redis is not source of truth" lesson,
  ignored the first time.
