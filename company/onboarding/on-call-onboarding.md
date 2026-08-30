---
title: On-call onboarding
category: onboarding
author: Ben Ortiz
team: SRE
created: 2024-02-05
updated: 2026-06-30
status: current
version: 3.2
---

# On-call onboarding

This is how new engineers join the pager rotation. Nobody goes on the
pager in their first 30 days. Nobody goes on the pager as primary
without at least two shadow shifts.

## Which rotation?

We have two rotations:

- **App on-call** — Portal, Beacon, Ledger, Gatekeeper, Compass, Relay.
  Typically staffed by Product Eng, Growth Eng, and Security engineers.
- **Platform on-call** — Aurora, Pulse, Atlas, Cartograph, and everything
  cluster/infra-level. Typically staffed by Platform, Ingest, Data, and
  SRE.

Your team lead will tell you which one you're joining. A few generalist
engineers are on both (rare, and not expected of you).

## The path

1. **Read the primer.** `runbooks/on-call-primer.md`. Covers PagerDuty
   layout, escalation policy (primary → secondary in 5 min → manager on
   duty), incident channels, and severity definitions.
2. **Read `runbooks/incident-response.md`.** This is the "what to do in
   the first 10 minutes of an incident" doc. Learn where the `#incidents`
   channel lives, what the IC role is, and how to start a bridge.
3. **Shadow the handoff meeting.** Monday 10:00 PT, on both rotations. It's
   ~20 min. You listen; you don't have to say anything.
4. **Shadow at least 2 shifts.** You're paired with the primary. You get
   paged (as an extra), you're in the channel, but you're not the IC and
   you're not on the hook. You should be actively working the alerts
   alongside them, not just reading.
5. **Go on as secondary for one rotation** (one week). Primary handles
   pages first; you get pulled in on escalation or when they need a hand.
6. **First primary shift.** With a designated buddy who is one Slack DM
   away for the full week.

Total time from start to first primary: usually ~6 weeks.

## Access you'll need

- **PagerDuty** — team lead adds you to the schedule; check that pager
  notifications on your phone work (SMS + push).
- **Datadog** — dashboards for your rotation are linked from
  `docs.mrdn.io/oncall/dashboards`.
- **AWS prod SSO role** — request via `SEC-xxxx` ticket to Security.
  Requires approval from your manager + Dara's team.
- **kubectl prod context** — added automatically once your SSO role is
  approved. Test with `kubectx meridian-prod && kubectl get ns`. All
  destructive verbs require an MFA touch.
- **ArgoCD prod app write** — team-scoped, requested with your prod SSO.
- **Runbook repo** — read access is default; write access requested with
  a note to `#platform`.

## What "being on-call" actually looks like

- One week at a time. Monday 10:00 PT to the following Monday 10:00 PT.
- Carry the pager (phone, obviously). Don't be more than ~30 min from a
  laptop.
- Expected response time to a page: **5 minutes acknowledge, 15 minutes
  substantive**. If you can't hit those, page your secondary early —
  don't wait for auto-escalation.
- Comp: on-call stipend + time-off for weekend pages (see people docs).
- Handoff on Monday: 20-min meeting, walk through open alerts,
  outstanding runbook improvements, anything the next person should
  know.

## What to do the first time you get paged

1. Ack in PagerDuty within 5 minutes.
2. Join `#incidents` (or the auto-created incident channel if the alert
   fires a SEV).
3. If it's a SEV: declare IC (probably you) and start a bridge. See
   `runbooks/incident-response.md`.
4. Look at the alert's linked runbook. If there isn't one, that's a
   bug — file a `PLAT-xxxx` after the incident.
5. Ask for help early. Nobody has ever been criticized for pulling in
   the secondary too soon; several have for waiting too long.

## Related docs

- `runbooks/on-call-primer.md`
- `runbooks/incident-response.md`
- `runbooks/rotate-production-secrets.md`
- `postmortems/` — read the last ~6 months before your first shift
