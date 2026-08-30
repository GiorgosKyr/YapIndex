---
title: "INC-2024-11-14: Duplicate Stripe charges on Nov 13 invoices"
category: incident
author: Tomás Herrera
team: Growth Eng
created: 2024-11-14
updated: 2024-11-15
status: resolved
version: 1.2
---

# INC-2024-11-14 — Duplicate Stripe charges

- **Severity:** SEV-1
- **Status:** Resolved
- **Detected:** 2024-11-14 07:48 PT via customer support ticket volume spike
- **Resolved:** 2024-11-14 18:22 PT
- **PagerDuty:** PD-INC-B02177
- **Slack channel:** `#inc-2024-11-14`
- **Responders:** Tomás Herrera (IC), Ravi Patel, Lin Zhao (customer comms),
  Elena Vasquez (Portal billing UI), Ben Ortiz (SRE support)

## Summary

Starting at ~07:30 PT on Nov 14, Support started receiving customer emails
reporting duplicated charges against their Nov 13 monthly invoices. By 08:15
PT, ~90 tickets were open on the same theme. Investigation showed that
Stripe had emitted `invoice.payment_succeeded` webhooks twice for a subset
of Nov 13 invoices due to a transient Stripe-side issue that triggered their
retry logic. Ledger's `POST /webhooks/stripe` handler had no idempotency
guard on `event.id` and processed both deliveries, resulting in a second
charge attempt via the Stripe API.

## Impact

- **Customers affected:** 178 workspaces.
- **Excess amount charged:** $214,318.44 (aggregate).
- **Financial disposition:** All duplicate charges refunded same day via
  Stripe `refunds.create`. Refund IDs logged to `#inc-2024-11-14`.
- **Reputational:** Lin sent a personalized apology email from
  `billing@meridiandata.io` to every affected workspace by 20:00 PT.

## Timeline (all times PT unless noted)

- **~03:00 (Nov 14)** — Stripe experiences internal degradation on their
  webhook delivery worker (per Stripe status page RCA published Nov 16).
  Delivery retries begin.
- **03:14 – 04:52** — Meridian's `POST /webhooks/stripe` receives 178
  duplicate `invoice.payment_succeeded` events, each with the same
  `event.id` as the earlier delivery. Ledger has no `event.id` dedupe.
  For each duplicate, Ledger calls `stripe.PaymentIntents.create` again.
- **07:30** — First customer emails arrive.
- **07:48** — Lin escalates to on-call; Tomás paged (`ledger-service`).
- **08:12** — Tomás confirms in Ledger logs that duplicate PaymentIntent
  IDs were created for the same invoice ID. Declares SEV-1.
- **08:35** — Stripe webhook endpoint temporarily disabled at the ALB
  (return 503) to stop the bleeding while a fix is developed. Stripe will
  retry with backoff, safely.
- **09:10** — Hotfix PR opened: add in-memory `event.id` set with 24h TTL
  (Redis-backed). PR-4471 in `ledger-service`.
- **09:55** — Hotfix reviewed, merged, deployed via ArgoCD.
- **10:20** — Webhook endpoint re-enabled. Backlog of retried webhooks
  drains cleanly; duplicates ignored.
- **11:00 – 17:00** — Full list of duplicate charges reconciled from Ledger's
  `charge_events` table joined against Stripe `PaymentIntent` list. Refunds
  scripted and executed in batches of 25.
- **17:45** — All 178 refunds confirmed successful in Stripe.
- **18:22** — Incident closed.

## Mitigation

1. Redis-backed dedupe on `event.id` (hotfix, TTL 24h). Not the durable
   fix; see postmortem for the follow-up `processed_stripe_events` table.
2. All duplicate charges refunded.
3. Customer comms sent by Lin from `billing@meridiandata.io`.

## Follow-up

See `postmortems/2024-11-14-duplicate-charges.md`.
