---
title: Meeting notes — ECS→EKS cutover planning
category: meeting-notes
author: Priya Ramanathan
team: Platform
created: 2024-03-15
updated: 2024-03-15
status: current
version: 1.0
---

# 2024-03-15 — ECS → EKS cutover planning

Room: Ravier (SEA HQ) + Zoom
Time: 14:00–15:10 PT
Scribe: Priya

## Attendees
- Priya Ramanathan (Platform, chair)
- Ravi Patel (CTO)
- Marcus Oduya (VP Eng)
- Ben Ortiz (SRE)
- Wen Liu (Ingest)
- Jae-won Park (Data)
- Elena Vasquez (Product Eng)
- Tomás Herrera (Growth Eng) — remote
- Dara Okonkwo — NOT YET HIRED, N/A
  (someone please own the security review interim — Ravi?)

## Agenda
- Confirm cutover window (Mon 2024-03-18)
- Service-by-service readiness
- Rollback plan
- Comms

## Notes

- Cutover window: **Mon 2024-03-18, 05:00–07:00 PT**. Traffic is
  ~lowest then. Confirmed with Sam for customer comms window.
- Order of cutover:
  1. Stateless: Beacon, Portal (behind CF, DNS-swap style)
  2. Compass, Relay, Lighthouse
  3. Ledger (needs Stripe webhook endpoint swap — Tomás owns)
  4. Aurora + Pulse — LAST. Ingest can tolerate a few min of 5xx (SDK
     retries). Do not do these until 1–3 are green.
- Ravi asked whether "Project Kraken" is on track for the same window —
  Jae-won corrected: **Kraken is the ClickHouse cluster project, not the
  ECS→EKS one.** This one doesn't have a codename, we've just been
  calling it "the March migration." (Nobody actually calls it Project
  Kraken. Priya to send a note to the team channel.)
- Datadog rollout status: still trialing, not blocker for cutover. We
  keep New Relic + CloudWatch as the primary observability for cutover
  day. Datadog dashboards used as a secondary view.
- Wen: Aurora config depends on ECS task metadata endpoint in ~2
  places. Ported to IMDSv2 / downward API, deployed to staging last
  week, looks good. One remaining TODO: the health check on the ALB
  target group changes shape.
- Elena: Portal has a hardcoded ECS service discovery name in one place
  (`beacon.internal-old`). Being replaced by k8s service DNS
  (`beacon.default.svc.cluster.local`) — PR open.
- Tomás: **billing service still writes usage counters directly to
  Redis**. Not touched by this migration, works the same on EKS. Just
  noting for the record.
- Ben: rollback = flip Route53 weighted records back to ECS ALBs.
  Terraform for both stacks is being kept in sync until 2024-04-15 (a
  month after cutover) at which point we tear down ECS.

## Risks
- CoreDNS: Ben has increased replicas to 5 for cutover. PDB set to
  `minAvailable: 3`. (Note: revisit before 1.29 upgrade later this year.)
- Kafka connectivity from EKS nodes: sec group verified, tested via
  staging.
- Cert-manager: Let's Encrypt rate limit — Priya pre-issued the wildcards.

## Action items
- [ ] Priya — send correction re: "Project Kraken" naming to
      `#eng` (this week)
- [ ] Wen — finish Aurora ALB health check port change (by Sun 03-17)
- [ ] Elena — merge Portal service discovery PR (by Fri 03-15 EOD)
- [ ] Tomás — confirm Stripe webhook endpoint swap tested against
      staging (by Sun)
- [ ] Ben — write final go/no-go runbook, review in `#platform` Sun
      evening
- [ ] Marcus — draft customer comms for Sam (this evening)
- [ ] Ravi — cover security review for cutover; formal security review
      resumes when Dara starts in Q3

## Next meeting
- Sunday 2024-03-17, 17:00 PT — go/no-go
