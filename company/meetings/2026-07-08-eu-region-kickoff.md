---
title: Meeting notes — EU region (Frankfurt) kickoff
category: meeting-notes
author: Priya Ramanathan
team: Platform
created: 2026-07-08
updated: 2026-07-08
status: current
version: 1.0
---

# 2026-07-08 — EU region kickoff (Frankfurt)

Zoom + Pioneer Square meeting room "Ravier".
~50 min.

## Attendees
- Priya Ramanathan (Platform, driving)
- Ravi Patel (CTO)
- Marcus Oduya (VP Eng)
- Ben Ortiz (SRE)
- Wen Liu (Ingest)
- Jae-won Park (Data)
- Elena Vasquez (Product Eng)
- Tomás Herrera (Growth Eng — Compass is on the critical path)
- Dara Okonkwo (Security)
- Sam Whitfield (Product)

Not present: Lin (out this week — Sam will brief her).

## Goal for the kickoff
Agree the shape of the thing, decide the phasing, name the leads.
Not a design review. Design docs come next.

## Where we are today
- All production traffic in `us-west-2`.
- DR in `us-east-1` is warm-standby for Postgres + S3 CRR only. No
  active traffic.
- EU customers currently served from us-west-2. This is a growing
  problem — 3 enterprise deals have listed data residency as a
  requirement in the last 2 quarters. Sam confirms.
- Target: **eu-central-1 (Frankfurt)**. GA target end of Q4 2026,
  though realistically some pieces will slip into Q1 2027.

## Scope (rough, first pass)
- New AWS account: `meridian-prod-eu` (already provisioned by Ben).
- New EKS cluster, ClickHouse cluster, MSK, Postgres RDS.
- Data residency **toggle at workspace level** (Sam / product decision):
  workspace is pinned to a region at creation. No cross-region moves
  in v1.
- Portal: `portal.eu.meridiandata.io` — same Portal codebase, region
  determined by workspace routing after login.
- API: `ingest.eu.meridiandata.io`, `api.eu.meridiandata.io` — same
  services, region-local data.

## Dependencies
- **Compass** (onboarding) — needs to know which region to provision a
  workspace in. Tomás: adding a region field to the signup flow; simple
  UX (dropdown, EU default for EU IPs).
- **Gatekeeper** — has to be region-aware for JWT scope. Dara says the
  cleanest option is a single global auth plane with region claims in
  the JWT. Ravi: agreed, don't fragment identity.
- **Ledger** — global. Billing stays in us-west-2 (customer money is
  not personal data under GDPR in the same way). Tomás to confirm with
  legal.
- **Cartograph** — schemas replicated per-region; source of truth
  per-region. No global schema. Jae-won: fine.
- **Relay** — needs egress from the EU region. Straightforward.

## Not in scope for v1
- Cross-region reads.
- Moving an existing workspace between regions.
- EU-hosted marketing site or docs (docs.mrdn.io stays global; that's
  fine, it's public).

## Risks
- **Latency for auth**: single global auth plane means EU users hit
  us-west-2 Gatekeeper. Priya: acceptable if we're careful with token
  TTL and refresh cadence. Dara agrees.
- **Datadog cost** — new site, new ingestion. Ben to model.
- **ClickHouse operational load** — running two clusters. Jae-won:
  we've been wanting to write down cluster ops as code anyway,
  forcing function.
- **Legal / DPA updates** — Dara + Nadia to coordinate.

## Phasing (rough)
1. **Foundation (Jul–Aug 2026)**: AWS account, VPC, EKS, base infra,
   IAM, observability wired up.
2. **Data plane (Aug–Sep)**: ClickHouse cluster, MSK, Postgres. Empty
   but functional.
3. **Services (Sep–Oct)**: deploy Aurora, Pulse, Beacon, Portal, Relay
   to EU cluster. Compass region-aware.
4. **Beta (Oct–Nov)**: 2–3 friendly EU customers, provisioned into
   EU region. Watched carefully.
5. **GA (target end of Q4)**: open self-serve region choice in Compass.

## Action items
- [ ] Priya — design doc for region topology + auth plane. Draft
      2026-07-22.
- [ ] Ben — Terraform for `meridian-prod-eu` VPC + EKS. Target
      2026-08-15.
- [ ] Tomás — Compass region-selection UX + backend. Design doc
      2026-07-31.
- [ ] Jae-won — ClickHouse cluster ops-as-code doc. 2026-08-31.
- [ ] Dara — DPA + GDPR review with legal. Ongoing.
- [ ] Sam — customer-facing framing + comms plan for EU launch.
- [ ] Marcus — weekly EU-region sync starting 2026-07-15, Wednesdays.

## Next
- Weekly sync: Wed 10:00 PT / 19:00 CET starting 2026-07-15
- Channel: `#proj-eu-region`
