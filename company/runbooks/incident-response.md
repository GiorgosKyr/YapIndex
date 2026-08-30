---
title: Incident Response
category: runbook
author: Ben Ortiz
team: SRE
created: 2024-08-20
updated: 2026-04-10
status: current
version: 3.0
---

# Incident Response

The full flow for handling a SEV-1 or SEV-2 at Meridian, from declaration
to postmortem. For the first 5 minutes of a page, see
`runbooks/on-call-primer.md`.

## Preconditions

- A page has been acknowledged and severity declared (SEV-1 or SEV-2).
  SEV-3s do not use this runbook.
- `#eng-oncall` and a dedicated incident channel (see step 2) are open.
- You have access to Statuspage.io (`status.meridiandata.io`) with the
  "publisher" role. Ask Lin Zhao if not.

## Roles

Every SEV-1/SEV-2 has three roles. One person may hold two if the
incident is small, but never all three.

- **Incident Commander (IC)** — drives the response. Decides mitigations,
  keeps timeline, calls escalations. Not usually the person hands-on-
  keyboard debugging.
- **Comms** — updates the status page, drafts customer emails, keeps
  `#customer-comms` in the loop. Default: Lin Zhao (Head of Support) or
  a delegate she nominates.
- **Scribe** — captures timeline in the incident doc: who did what and
  when. Enables the postmortem.

Hands-on-keyboard engineers report to the IC, not to their manager, for
the duration.

## Steps

### 1. Declare and open the incident

- IC types in `#eng-oncall`:
  > `/incident declare sev2 "Beacon 500s on cohort endpoints"`
- The bot creates:
  - Dedicated channel `#inc-YYYYMMDD-<slug>`.
  - Incident doc from template (Google Doc) with headers: Summary,
    Timeline, Actions, Mitigations, Follow-ups.
  - Zoom bridge (auto-linked from the channel topic).

### 2. Post initial status

- Comms posts a status-page holding message within 10 min of declaration
  for any SEV-1 or externally-visible SEV-2:
  > "We are investigating elevated errors on <component>. Next update in
  > 30 minutes."
- The status page uses these components: Portal, Ingest API, Query API,
  Dashboards, Auth, Billing.
- Never publish root cause or customer names in the status page.

### 3. Investigate and mitigate

- IC keeps a running "current hypothesis" pinned in the incident channel.
- Prefer mitigation over root-cause. Reasonable mitigations:
  - Roll back the most recent deploy (`runbooks/deploy-current.md` §
    Rollback).
  - Scale up affected consumers (Pulse, Beacon).
  - Disable a feature flag in LaunchDarkly.
  - Move a hot workspace to the overflow topic
    (`runbooks/kafka-partition-rebalance.md` § 3).
- If the mitigation involves customer-visible degradation (e.g.
  disabling a feature), comms updates the status page.

### 4. Status-page cadence

- SEV-1: update every 30 min minimum, even if the update is "still
  investigating".
- SEV-2: update every 60 min.
- On resolution, post "Resolved" and keep incident visible for 24 h.

### 5. Resolve

- IC declares resolution in the channel and in the bot:
  > `/incident resolve`
- Comms posts final status-page update and, for SEV-1, a customer
  email drafted with Lin Zhao (Head of Support). Enterprise-tier
  customers get a direct CSM outreach in addition.
- Scribe closes out the timeline.

### 6. Postmortem

- Postmortem is due **5 business days** after resolution.
- Owner: usually the IC, unless reassigned. Uses the postmortem template
  in `postmortems/`.
- Blameless. Focus on contributing factors, not people.
- Review meeting scheduled within 10 business days; VP Eng attends for
  SEV-1s.
- Follow-up action items land in Linear with the `incident-followup`
  label; owners must be individuals, not teams.

## Verification (of the response, not the incident)

At close of incident:
- Statuspage.io shows the correct final state on all affected components.
- Incident doc has: severity, timeline, resolution timestamp, IC name,
  comms name, scribe name.
- PagerDuty incident is resolved.
- `#customer-comms` has been informed of the resolution.

## Rollback

If you resolve prematurely and the issue recurs:
- Re-declare with the same slug: `/incident declare sev2 "<slug> (recur)"`.
- Update the same status-page incident (do not open a new one) if within
  the same rolling hour.
- Note the false resolution in the postmortem timeline.

## Contacts

- Incident commander rotation: `@incident-commander` (PagerDuty)
- Comms default: Lin Zhao (`@lin`)
- Status-page admin: Lin Zhao, backup Ben Ortiz
- Legal/PR escalation (data exposure only): Dara Okonkwo → Nadia Chen
