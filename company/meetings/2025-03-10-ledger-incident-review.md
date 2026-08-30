---
title: Meeting notes — INC-2025-03-08 Ledger incident review
category: meeting-notes
author: Tomás Herrera
team: Growth Eng
created: 2025-03-10
updated: 2025-03-10
status: current
version: 1.0
---

# 2025-03-10 — Ledger overbilling review (INC-2025-03-08)

Zoom. 30 min. Blameless. Recording in `#incidents`.

## Attendees
- Tomás Herrera (Growth Eng lead, IC on the incident)
- Ravi Patel (CTO)
- Marcus Oduya (VP Eng)
- Ben Ortiz (SRE)
- Priya Ramanathan (Platform)
- Dara Okonkwo (Security)
- Nadia Chen (partial — first 10 min)
- Lin Zhao (Support, partial)

## Purpose
Review the incident, agree on root cause, agree on immediate remediation
and longer-term ADR. No blame.

## Recap
- 2025-03-08 ~03:40 PT: Redis (ElastiCache) memory pressure on the
  Ledger cache; eviction kicked in.
- Usage counters (per-account monthly billable event totals) lived in
  Redis and were treated as the source of truth by the invoicing tick.
- Counters for ~62 accounts got evicted. On next tick, Ledger read `0`,
  interpreted as "hasn't been billed this cycle", and issued charges
  again for accounts that had already been invoiced. ~$41k in
  duplicate charges before pause.
- Tomás paused the invoicing worker at 04:12 PT. Refunds initiated by
  end of day.

## Discussion

- **Root cause, agreed:** Redis was the source of truth for
  money-relevant state. That's the class-of-error, not the eviction
  itself. Under memory pressure Redis is *supposed* to evict.
- Ben: we do have a "no source-of-truth in cache" rule floating around
  but it's not written down as an ADR anywhere. Time to make it one.
- Priya: the Ledger service predates the current architectural
  guidelines. It made sense in 2022 to put counters in Redis for speed.
  It stopped making sense a while ago.
- Dara: from a controls standpoint, we now need an audit trail for
  any counter-increment for money reasons. Postgres gives us that; Redis
  doesn't (easily).
- Marcus: comms — we're going to write a public postmortem (customer-
  facing, condensed). Sam is drafting.
- Ravi: extend the pause on the invoicing worker for one more billing
  tick while the fix is in flight. Manual invoicing for anyone who
  needs it before then, Lin's team owns exceptions.

## Action items
- [ ] Tomás — write **ADR-0044 (Usage counters source of truth)**.
      Postgres authoritative, Redis a read-through cache with TTL. Draft
      by 2025-03-14.
- [ ] Tomás — migration plan: dual-write for 2 weeks, then flip reads,
      then remove Redis path. Rough target end of Q2.
- [ ] Ben — write the "no cache-as-SoT for money" doc into the
      architecture principles page (`docs.mrdn.io/eng/principles`).
- [ ] Dara — add a control to the SOC 2 program: monthly review that
      no billing-relevant state lives in a cache.
- [ ] Sam — public postmortem draft by 2025-03-12.
- [ ] Lin — track customer refund status; report back at next Growth Eng
      standup.
- [ ] Marcus — schedule a follow-up in 6 weeks (~2025-04-21) to check
      migration progress.

## Not action items but worth remembering
- Beacon-Aggregator has a similar shape (cache-fronted counters). It's
  not billing-relevant so it's not the same severity, but the same
  question applies. Elena, please look and decide. — Priya
