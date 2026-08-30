---
title: "Postmortem: Duplicate Stripe charges (2024-11-14)"
category: postmortem
author: Tomás Herrera
team: Growth Eng
created: 2024-12-02
updated: 2024-12-06
status: current
version: 1.1
---

# Postmortem — 2024-11-14: Duplicate Stripe charges

> Related incident: `incidents/INC-2024-11-14-duplicate-charges.md`
> Blameless. The system allowed the charges; we're fixing the system.

## Summary

Between 03:14 and 04:52 PT on 2024-11-14, Stripe re-delivered 178
`invoice.payment_succeeded` webhooks that Ledger had already
processed. Ledger's `POST /webhooks/stripe` handler did not
deduplicate on `event.id` and, for each replayed event, called
`stripe.PaymentIntents.create` again against the same invoice. 178
customer workspaces were double-charged, totalling $214,318.44. All
charges were refunded within 12 hours of discovery. Same-day
personalized apology emails went out from Lin.

## Impact

- Customers charged twice: 178.
- Total incorrect charge amount: $214,318.44.
- Refund latency: 4 – 14 hours from original duplicate charge.
- Support ticket volume: ~230 tickets on Nov 14, ~40 on Nov 15,
  trailing off. All resolved within 5 days.
- Two Growth-tier workspaces have since noted this incident in
  renewal discussions but have not churned as of this writing.

## Timeline (PT)

- **Nov 14 03:00 (approx)** — Stripe experiences internal webhook
  delivery degradation. Their retry logic begins re-delivering
  successful events.
- **03:14 – 04:52** — 178 `invoice.payment_succeeded` events
  re-delivered to `POST /webhooks/stripe`. Each is processed as if
  new. `stripe.PaymentIntents.create` invoked for each; each succeeds.
- **07:30** — Customers begin emailing Support.
- **07:48** — Ticket-volume spike escalated; Tomás paged.
- **08:12** — Root cause identified: duplicate PaymentIntent IDs
  against the same invoice; no dedupe on `event.id`.
- **08:35** — ALB configured to return 503 on `/webhooks/stripe` to
  stop the bleeding.
- **09:10** — Hotfix PR-4471 opened: Redis-backed dedupe on
  `event.id`, 24h TTL.
- **09:55** — Deployed via ArgoCD.
- **10:20** — Webhook endpoint re-enabled.
- **11:00 – 17:00** — Duplicate charges reconciled and refunded in
  batches.
- **17:45** — All refunds confirmed.
- **18:22** — Incident closed.
- **19:00 – 22:00** — Personalized apology emails sent.

## Root cause

The Ledger webhook handler treated every incoming Stripe event as a
new event. Idempotency in Stripe is the responsibility of the
receiver — Stripe explicitly documents that webhooks may be
delivered more than once. Our handler did not honor this contract.

Concretely, `ledger/webhooks/stripe.py:handle_invoice_payment_succeeded`
went straight from `verify_signature(payload)` to
`process_invoice_payment(invoice_id)`. There was no lookup of
`event.id` against a "have we seen this?" store.

## Contributing factors

- **Redis was ambiently treated as source of truth for money-adjacent
  state** (see also INC-2025-03-08). Even the hotfix reached for
  Redis as the dedupe store, which we later replaced with a Postgres
  table (`processed_stripe_events`) for durability. This pattern
  cost us again in March 2025.
- **No load-testing of webhook retries.** Our webhook tests were
  happy-path only. We had never asked "what if Stripe sends the
  same event twice?" in a test.
- **No anomaly monitor on invoice generation.** A 2x spike in a
  single day, or >2 invoices per customer in 24h, was not alerted
  on — even though it would have caught this in the first hour.
- **Manual refund tooling.** The refund script had to be written on
  the fly. A pre-built "refund by invoice list" tool would have
  saved 2–3 hours of the response.

## What went well

- Once escalated, root cause was found in ~25 minutes.
- Decision to disable the webhook endpoint (return 503) rather than
  keep processing while investigating was the right call and
  prevented further damage. Stripe's retry-with-backoff meant no
  events were ultimately lost.
- Customer comms were personal, honest, and timely. Lin's emails
  set an internal bar for how we handle billing incidents.
- Cross-team coordination (Growth Eng, SRE, Support) was cooperative
  and low-drama.

## What went poorly

- We knew Stripe webhooks can be duplicated. It's in their docs. We
  did not implement dedupe.
- The gap between the original double-charge (03:14 PT) and
  detection (07:48 PT) was ~4.5 hours. An anomaly monitor could
  have compressed this to minutes.
- Redis was the reflexive choice for dedupe. We had to revisit this
  in the ADR-0044 aftermath of a later incident.
- No formal comms plan existed for billing incidents. Lin invented
  the template on the day.

## Action items

| # | Owner | Description | Status | Due |
|---|-------|-------------|--------|-----|
| 1 | Tomás | **Add `processed_stripe_events` Postgres dedup table.** `event.id` is the primary key. Ledger inserts before processing; on conflict, no-op. Replaces the Redis-only hotfix. | done | 2024-12-15 |
| 2 | Tomás | Load-test Stripe webhook retries against staging. Include duplicate delivery, out-of-order delivery, and long-tail retry (>24h). | done | 2025-01-10 |
| 3 | Elena / Tomás | Alert on invoice generation anomalies: `>2 invoices per customer in 24h`, or aggregate invoice-count YoY delta >30%. Datadog `dd:monitor/40118`. | done | 2024-12-20 |
| 4 | Tomás | Build a "refund by invoice list" internal tool in the Ledger admin UI. Includes dry-run mode and CSV export. | done | 2025-01-24 |
| 5 | Lin / Sam | Standing billing-incident comms template. Approval path defined. | done | 2024-12-19 |
| 6 | Tomás | Every webhook handler in Ledger reviewed and confirmed idempotent (not just Stripe). Postmark, WorkOS webhooks also audited. | done | 2025-01-31 |

## References

- `backend/ledger-service.md` — updated 2024-12-16 to document the
  `processed_stripe_events` table and idempotency contract.
- `adrs/0044-usage-counters-source-of-truth.md` — different problem
  (usage counters), same underlying "Redis is not source of truth"
  lesson. This incident was one of the inputs.
- `runbooks/handle-billing-incident.md` — new, based on this
  response.
