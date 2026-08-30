---
title: Security Review Process
category: security
author: Dara Okonkwo
team: Security
created: 2024-10-15
updated: 2026-04-08
status: current
version: 2.0
---

# Security Review Process

Every new service, and every "major change" to an existing service,
goes through a security review before it ships to production. The point
is not to be a gate — it's to make sure someone who is not the author
has thought about how the change could go wrong.

Owner: **Security team** (Dara Okonkwo's team, 3 engineers).

## When a review is required

Required:

- **New service** — anything that shows up on the canonical services
  list (canon §4) requires a review before its first prod deploy.
- **New public API surface** — a new endpoint on Aurora or Beacon that
  is customer-reachable.
- **New authentication or authorization path** — anything that produces,
  consumes, or validates a JWT; anything that changes what Gatekeeper
  says.
- **New data flow** — a change in what data is stored where, or a new
  export path to a third party.
- **New third-party vendor** that will process customer data or hold
  production credentials.
- **New IAM role/policy** in the `meridian-prod` account.
- **Changes to Ledger** touching billing calculations, Stripe webhooks,
  or the `usage_counters` / `processed_stripe_events` tables.

Not required (author's discretion, but encouraged for a quick chat):

- Refactors that don't change data flow or trust boundaries.
- New reports/dashboards.
- Configuration tweaks within an existing service.

If you are not sure, ask in `#sec-review` on Slack.

## Process

1. Open a Jira ticket under project **`SEC`** with the label
   `security-review`. Ticket key looks like `SEC-1247`.
2. Attach:
   - A short design doc (1–2 pages is fine).
   - A threat model — STRIDE for API-shaped things, a data flow diagram
     for anything ingesting or exporting data.
   - The threat model / security review checklist filled in (link in the
     Jira ticket template).
3. Security triages within one business day and assigns a reviewer.
4. Reviewer either signs off, requests changes, or escalates to Dara.

## SLA

**Five business days** from ticket creation to a first response
(sign-off or actionable feedback). Sign-off itself can take longer if
follow-ups are needed, but the first-response clock is five days.

If Security is going to miss the SLA, the reviewer posts in
`#sec-review` and pings the requester. Missed SLAs are tracked and
reported to VP Eng monthly.

## Threat model checklist (excerpt)

The full checklist is in the Jira template; a taste:

- What data does this touch? Is it customer data, employee data,
  billing data, secrets?
- Who can call the new endpoint(s)? Does the answer match what the OPA
  policy currently says (see `security/authorization.md`)?
- Are new secrets introduced? Are they in Secrets Manager? Are they on
  the rotation calendar? (`security/secrets-rotation.md`)
- Does the change alter what ends up in logs? (INC-2024-08-05 was
  caused by a JWT ending up in a log line.)
- Does the change alter the shape of a Stripe webhook handler?
  (INC-2024-11-14 was caused by a missing dedup.)
- If the change touches Ledger's `usage_counters`, has Growth Eng
  reviewed for the ADR-0044 constraint (Postgres is authoritative,
  not Redis)?

## Related

- `security/authentication.md`
- `security/authorization.md`
- `security/secrets-rotation.md`
- `security/compliance-soc2.md`
