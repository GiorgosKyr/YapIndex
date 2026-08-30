---
title: Support Escalation Policy
category: support
author: Lin Zhao
team: Support
created: 2024-10-04
updated: 2026-06-15
status: current
version: 3.1
---

# Support Escalation Policy

This document describes how Meridian Support escalates tickets internally.
For customer-facing SLAs see `support/customer-tiers.md`.

## Roles

- **L1:** Front-line support engineers. Handle account questions, how-to,
  known issues, most billing questions.
- **L2:** Senior support + product specialists. Handle complex product
  questions, data investigations, and initial API debugging.
- **Engineering on-call:** Two rotations (App and Platform, see
  `runbooks/on-call-primer.md`). Paged only for confirmed service
  degradation or hard blockers.
- **CSM (Customer Success Manager):** Named contact for Scale +
  Enterprise. Owns strategic escalations and multi-touch resolution.
- **Duty Manager:** L2 lead on rotation, weekly handoff. Approves
  policy exceptions (e.g., waiving overage, extending trials).

## Ticket severity (as set by Support, not customer)

| Sev | Definition | Example |
|-----|------------|---------|
| S1 | Customer's production is broken because of Meridian. | Ingest returning 5xx for a customer's traffic; billing double-charge. |
| S2 | Feature broken but workaround exists; or data delay >30 min. | Cohorts endpoint slow; dashboard shows stale data. |
| S3 | Question or minor bug. | "How do I export CSV?" |
| S4 | Feature request, feedback. | "Please add a Slack notification integration." |

## Escalation triggers

**Escalate L1 → L2 when:**
- Ticket has been open >2h without progress on a Scale+ workspace.
- Investigation needs API log lookup or ClickHouse query.
- Customer explicitly asks for engineering context.

**Escalate L2 → Engineering on-call when:**
- **Any S1** — page immediately via PagerDuty (`meridian-support-escalations`).
- **S2** with confirmed service-side degradation.
- Suspected security issue — page **Security** (Dara's rotation),
  not on-call.

**Escalate to CSM when:**
- Enterprise customer, any severity, first touch.
- Scale+ customer with recurring pain (>3 tickets same area in 30 days).
- Anything that touches renewal or expansion conversations.

## Communication

- Internal comms live in **`#support-escalations`**. S1 comms
  simultaneously in **`#incidents`**.
- Customer comms via Zendesk. Enterprise customers optionally via
  Slack Connect.
- Status page updates for anything that affects >1 workspace: coordinate
  with SRE (Ben Ortiz's team) per `runbooks/incident-response.md`.

## When Support triggers an incident

For a confirmed S1 with customer impact:
1. Page App on-call OR Platform on-call (depending on affected service —
   ingest/pipeline → Platform; app-layer → App).
2. Open `#inc-<date>` channel per incident response runbook.
3. Support duty manager acts as **Communications Lead** until a
   dedicated IC takes over.

## Historical note

Escalation policy was significantly tightened after
[INC-2024-11-14](../incidents/INC-2024-11-14-duplicate-charges.md) — the
duplicate-charge incident. Prior to that, billing anomalies were treated
as L2 issues. They are now S1 by default.

## Owner

Lin Zhao. Reviewed quarterly.
