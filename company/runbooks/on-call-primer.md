---
title: On-Call Primer
category: runbook
author: Ben Ortiz
team: SRE
created: 2024-08-01
updated: 2026-06-20
status: current
version: 2.5
---

# On-Call Primer

Read this before your first shift. It covers the first 5 minutes of a page,
severity definitions, and the escalation chain.

Meridian runs two rotations (see canon §12):
- **App on-call** — Portal, Beacon, Ledger, Gatekeeper, Compass, Relay.
- **Platform on-call** — Aurora, Pulse, Atlas, Cartograph, infra, k8s.

Weekly handoff Mondays 10:00 PT. Primary + Secondary, PagerDuty-managed.

## Preconditions

- PagerDuty account with the correct schedule assigned.
- Access to `#eng-oncall` in Slack.
- Datadog SSO working (`app.datadoghq.com` → Meridian org).
- ArgoCD login (`argocd login argocd.mrdn.io --sso`).
- SSH key on file for the bastion (`bastion-01.prod.mrdn.io`).
- You have completed the on-call shadow rotation with the previous primary.

## Steps — First 5 minutes of a page

1. **Acknowledge the page in PagerDuty.** If you cannot within 5 minutes,
   it auto-escalates to the secondary and then to the manager on duty. Do
   not silence a page you have not investigated.
2. **Join `#eng-oncall`.** Post the incident in-thread:
   > "Investigating: `<alert name>`. Datadog link: <url>. Following up."
3. **Open the alert in Datadog.** Every alert links to a runbook via the
   `@runbook_url` annotation. Follow it. If the runbook is stale, file a
   Linear ticket after resolution.
4. **Declare severity** (see below). Post in `#eng-oncall`:
   > "Declaring SEV-2 on `<service>`: <symptom>. IC: me."
5. **If SEV-1 or SEV-2**, page the incident commander rotation
   (`/pd trigger incident-commander`). Follow
   `runbooks/incident-response.md` from here — you are almost certainly
   not going to run this alone.

## Severity definitions

| SEV | Definition | Response |
|-----|------------|----------|
| **SEV-1** | Customer-impacting outage: ingest is down, dashboards fail to load, billing incorrect, auth broken for > 5% of workspaces. | Page IC, comms, status page within 10 min. All hands available. |
| **SEV-2** | Degraded but not down: elevated errors (1–5%), delayed data (< 30 min), single non-critical service failing, one large customer affected. | IC required, status page if externally visible. |
| **SEV-3** | Internal-only: a background job failed, a non-blocking alarm, single-workspace issue that support can work around. | Handle during business hours. Notify but do not page IC. |

Do not undercall. It is always fine to declare SEV-2 and downgrade later.
Undercalling delays status-page comms and postmortems.

## Escalation chain

Timings per PagerDuty policy:

1. **Primary on-call** — 5 min ack window.
2. **Secondary on-call** — auto-paged if primary does not ack.
3. **Manager on duty** — auto-paged after another 5 min. This is the
   rotating team lead, not the CTO.
4. **Head of team** — Priya (Platform), Elena (Product Eng), Tomás
   (Growth Eng), Wen (Ingest), Jae-won (Data), Dara (Security), Ben (SRE).
5. **VP Eng** — Marcus Oduya, only for SEV-1 lasting > 30 min.
6. **CTO** — Ravi Patel, SEV-1 lasting > 90 min or any incident with
   customer-data exposure. Security team also pages Dara directly.

## Verification (that you are ready for a shift)

- Test-page yourself: `/pd test-notification` in Slack. You should get
  the SMS, push, and email you configured.
- Confirm Datadog notification routing is working:
  `monitor status:ok` search should show `On-Call: <your name>`.
- Confirm you can `argocd app sync <any>-staging` (dry run) from your
  laptop.

## Rollback / handoff

- If you become unable to hold the pager mid-shift, page the secondary and
  post in `#eng-oncall`. Update PagerDuty to override the schedule.
- End of shift: post a short handoff message in `#eng-oncall` naming any
  open incidents, watched dashboards, and pending follow-ups.

## Contacts

- SRE lead: Ben Ortiz
- Incident commander rotation: `@incident-commander` (PagerDuty)
- Support lead (comms during customer-facing incidents): Lin Zhao
