---
title: "ADR-0044: Postgres is the source of truth for billing usage counters"
category: adr
author: Tomás Herrera
team: Growth Eng
created: 2025-03-19
updated: 2025-04-02
status: Accepted
version: 1.1
---

# ADR-0044: Postgres is the source of truth for billing usage counters

## Context

On 2025-03-08 we shipped an incorrect batch of invoices to ~40 customers
totalling ~$62K in over-charges
([INC-2025-03-08](../incidents/INC-2025-03-08-ledger-overbilling.md),
[postmortem](../postmortems/2025-03-08-ledger-overbilling.md)).

The root cause was architectural: **Ledger treated Redis as authoritative
state for per-workspace usage counters.** Under memory pressure Redis
evicted counter keys (`allkeys-lru`). A subsequent recovery job rebuilt
from ClickHouse but a coding bug added the recovered amount on top of the
already-billed amount for the current cycle.

The underlying problem was allowing a cache to be treated as durable state
for financial data.

## Decision

1. **Postgres is authoritative.** All usage counters live in the
   Postgres table `usage_counters` (columns: `workspace_id`, `period_start`,
   `metric`, `count`, `updated_at`, `version`). Ledger reads and writes
   through Postgres, using row-level locks for updates within a cycle.
2. **ClickHouse is the recomputable source of truth.** For any dispute or
   discrepancy, the authoritative recomputation is done from ClickHouse
   over the actual event stream. Any deviation between Postgres and the
   ClickHouse recomputation is an incident.
3. **Redis is cache only.** Redis MAY cache read-heavy usage totals for
   Portal dashboard display with a short TTL (≤60s), but MUST NOT be
   read on the billing path. Redis MUST NOT be treated as durable state
   for any billing-related data, period.
4. **Idempotency at the Stripe boundary.** Ledger continues to dedupe
   Stripe webhook deliveries via the `processed_stripe_events` table
   (introduced after INC-2024-11-14). Invoice creation is idempotent
   keyed on `(workspace_id, period_start)`.

## Alternatives considered

- **Redis with AOF + separate persistence layer.** Improves Redis
  durability but doesn't fix the core "cache treated as truth" problem
  and adds ops burden. Rejected.
- **Move to a dedicated ledger DB (e.g. tigerbeetle).** Interesting long
  term. Not proportional to current scale. Revisit in 2027.

## Consequences

**Positive:**
- Financial correctness has a single authoritative store with backups,
  PITR, and audit history.
- ClickHouse remains the mathematical source-of-truth (events are the
  only true record).

**Negative:**
- Slightly higher latency on the billing hot path (Postgres roundtrip
  instead of Redis).
- Portal dashboards get their usage figures from Redis cache — will show
  slightly stale numbers (≤60s), which is acceptable and documented.

## Related

- Incident: `incidents/INC-2025-03-08-ledger-overbilling.md`
- Postmortem: `postmortems/2025-03-08-ledger-overbilling.md`
- Ledger service: `backend/ledger-service.md`
- Superseded implicit assumption: earlier `runbooks/redis-*.md` and some
  Growth Eng notes stated or implied Redis was authoritative. Those are
  incorrect from 2025-03-19 forward.

## Status

Accepted 2025-04-02. Implementation completed 2025-04-30. Migration of
existing Redis counter data was one-shot from ClickHouse recomputation.
