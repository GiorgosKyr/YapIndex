---
title: Weekly eng leads sync
category: meeting-notes
author: Marcus Oduya
team: Eng
created: 2026-08-12
updated: 2026-08-12
status: current
version: 1.0
---

# 2026-08-12 — Weekly eng leads

30 min. Zoom. Rough notes, sorry.

## Present
- Marcus, Priya, Jae-won, Elena, Tomás, Dara, Ben, Wen

## Round-robin

**Platform (Priya)**
- EU region: EKS up in staging-eu. Terraform for prod-eu 60% done. Ben
  covering while she's out next week.
- CoreDNS PDB review from Feb still open. Owner? Ben.
- Datadog spend up ~9% MoM. Need to look at index retention on the
  ingest logs.

**Data (Jae-won)**
- ClickHouse: cost-limit wrapper in Atlas is deployed, no regressions.
- Backfill for the Q4 export finally done (yes, 6 months late).
- Cartograph — small perf issue, `PLAT-4412`, not urgent.

**Product Eng (Elena)**
- v3 adoption at 91% of API traffic. v2 EOL 2026-11-01 still on track.
- Beacon-Aggregator: continuing the cache-as-SoT audit Priya asked for
  in March 2025. Nothing money-relevant, but there's one endpoint
  (`/cohorts/{id}/counts`) where stale cache reads could underreport.
  Not a bug, but worth an ADR eventually.
- Lighthouse alert templates — new pack shipping this week.

**Growth Eng (Tomás)**
- Ledger Postgres RDS at **78% CPU on Sundays** — probably the invoice
  cron. Not paging but not comfortable. Will look Monday.
  (Followup: possibly move the cron off Sunday peak, or shard the
  invoice batch.)
- Compass region-selection UX in review with Sam.
- Ledger v3 client cutover done ages ago, closed the ticket.

**Security (Dara)**
- Investigating a **potential Aurora rate-limit bypass** reported by a
  customer (Nordwind Cycles, `SEC-217`). Reproduced once in staging.
  Possibly related to how we compute the bucket key when
  `X-Forwarded-For` has multiple entries. Working with Wen.
- SOC 2 Type II annual review coming up in October, kickoff next week.

**SRE (Ben)**
- Last week: 2 low-sev pages, both self-cleared.
- CoreDNS PDB review — accepting the todo from Priya. This week.
- Datadog dashboards for EU region — starting once Priya's design doc
  lands.

**Ingest (Wen)**
- Kafka partition rebalance runbook is being updated after last week's
  onboarding of a new large customer (didn't page, but partition
  distribution got skewed again). ENG-3921.
- Working with Dara on the rate-limit thing.

## Cross-team

- v2 API EOL comms — Sam wants a joint sign-off from Elena + Lin next
  week that we're actually going to hold the 2026-11-01 date this
  time. Marcus: yes, hold the line unless we have a hard reason.
- Hiring: two open reqs on Platform, one on Data. Referrals welcome.

## Small things
- Reminder: on-call handoff notes should go in the PagerDuty schedule
  note, not just Slack.
- Tomás: someone please poke the office manager about the meeting room
  A/V — third Zoom drop this month.
- Priya OOO next week (Mon–Wed). Ben covering Platform.

## Action items
- [ ] Ben — CoreDNS PDB review, done this week
- [ ] Tomás — investigate Ledger Sunday CPU, report next week
- [ ] Dara — Aurora rate-limit bypass, update by next sync
- [ ] Wen — Kafka rebalance runbook update, target Fri
- [ ] Elena — pull Beacon-Aggregator cohort-counts audit into a written
      note, share in `#eng`

Next week: same time. Ben chairs (Priya out).
