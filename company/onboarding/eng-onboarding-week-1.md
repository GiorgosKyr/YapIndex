---
title: Engineering Onboarding — Week 1
category: onboarding
author: Marcus Oduya
team: Eng
created: 2023-06-01
updated: 2026-04-19
status: current
version: 2.6
---

# Week 1 goals

By the end of week 1, we want you to have:

1. **Shipped a small PR** to a real service in production or staging.
2. **Shadowed one on-call shift handoff** (Monday 10:00 PT).
3. **Read the top ADRs** so you understand why the system looks the way it
   does.
4. Met 1:1 with your manager, your buddy, and at least two people outside
   your team.

Nothing here is a hard gate — but if week 1 ends and none of the above
happened, tell your manager. Something's off.

## 1. Ship a small PR

Ask your buddy for something small. Good candidates:

- Fix a doc typo you noticed during onboarding (please).
- Bump a minor dep flagged by Renovate.
- Add a missing test to your team's service.
- Small refactor your buddy has been meaning to do.

Read `docs.mrdn.io/eng/pr-guidelines` before opening. Highlights:

- PRs go through GitHub. Ownership file (`CODEOWNERS`) auto-assigns reviewers.
- CI is GitHub Actions. Do not merge with a red build.
- ArgoCD picks up the change automatically on merge to `main` for staging.
  Prod deploys are PR-gated (a separate `deploy/prod` PR in the deployment
  repo, or auto for services on the ArgoCD auto-sync list).

## 2. Shadow on-call

Two rotations: **App on-call** (Portal, Beacon, Ledger, Gatekeeper,
Compass, Relay) and **Platform on-call** (Aurora, Pulse, Atlas,
Cartograph, infra, k8s). Handoff meeting is Mondays 10:00 PT. Join the
one that matches your team. See `on-call-onboarding.md` for the full
on-boarding path — you're not on the pager yet, just observing.

## 3. Top ADRs to read

These are the ones that most often come up in design discussions. If
someone in a meeting says "well, per ADR-forty-something…", it's
probably one of these:

- **ADR-0001** — Redis for session caching. The original informal one.
  Historical context.
- **ADR-0014** — Snowflake evaluation (rejected). Context for why we run
  our own analytics store.
- **ADR-0016** — ClickHouse adoption. The single biggest architectural
  decision in the company's history.
- **ADR-0022** — Kafka between Aurora and ClickHouse (introduction of Pulse).
- **ADR-0031** — ECS → EKS migration (the "March migration").
- **ADR-0044** — Usage counters source of truth (Postgres, not Redis).
  Written in response to INC-2025-03-08. Required reading if you touch
  Ledger, Beacon-Aggregator, or anything that reasons about billable
  events.

Later this quarter (once you're comfortable), also skim the API v3 design
doc — v2 sunsets 2026-11-01 and it's useful context for anything
customer-facing.

## 4. People to meet

- Your manager (weekly 1:1 from here on).
- Your buddy (daily for week 1, then trailing off).
- One person on a team you'll depend on (e.g. if you're on Product Eng,
  meet someone on Platform).
- One person from a totally different team (Support, Growth, Design).

## Things not to do in week 1

- Don't take a prod deploy solo.
- Don't rotate any production secret without a buddy watching.
- Don't merge to `main` in `terraform-live` — that repo has its own
  onboarding flow.
- Don't `kubectl exec` into prod pods. Use Datadog + logs first, then ask.
