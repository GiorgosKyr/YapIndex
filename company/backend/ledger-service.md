---
title: Ledger — Billing Service
category: backend
author: tomas.herrera@meridiandata.io
team: Growth Eng
created: 2022-12-01
updated: 2026-08-11
status: current
version: 5.1
---

# Ledger

Ledger is our billing service. It manages subscriptions, invoices, usage
metering, tax, and the Stripe integration. Internally, Growth Eng uses the
word "account" for what everyone else calls a "workspace" — the Postgres
schema uses `account_id` as the FK name, even though it points to
`workspaces.id`. Don't fix this; too much SQL depends on it.

## Runtime

- **Language:** Python 3.11
- **Framework:** FastAPI + Uvicorn.
- **Deployment:** EKS (us-west-2), 4-pod baseline, HPA to 12.
- **Owner:** Growth Eng (Tomás Herrera).

## Responsibilities

- Plans, subscriptions, seat/MTE quantities.
- Invoice generation via Stripe Billing (Stripe is the source of PDFs).
- Tax via Stripe Tax.
- Usage counters (metered MTEs, per workspace, per calendar month).
- Webhook receiver for Stripe events.
- Dunning + payment failure state machine, exposed to Portal.

## Endpoints (selected)

```
GET  /v3/accounts/{id}/subscription
POST /v3/accounts/{id}/subscription:change    # plan/quantity change
GET  /v3/accounts/{id}/invoices
GET  /v3/accounts/{id}/usage?period=YYYY-MM
GET  /v3/accounts/{id}/payment-methods
POST /webhooks/stripe                         # Stripe → Ledger
```

Route example:

```python
@router.post("/webhooks/stripe", status_code=204)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    session: AsyncSession = Depends(deps.db),
) -> Response:
    payload = await request.body()
    event = stripe.Webhook.construct_event(
        payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
    )
    if await already_processed(session, event.id):
        return Response(status_code=204)
    await handle_event(session, event)
    await mark_processed(session, event.id)
    return Response(status_code=204)
```

## Stripe webhook deduplication

Every webhook `event.id` is written to Postgres table
`processed_stripe_events` (columns: `stripe_event_id PK`, `type`,
`received_at`, `handled_at`). Handlers are only executed if the row does
not already exist. This dedup was added directly after INC-2024-11-14, when
Stripe's retry logic re-delivered ~180 `invoice.payment_succeeded` events
during a Ledger deploy blip and we double-charged customers. The full
handler runs inside the same transaction that inserts the marker row, so a
partial handle is impossible.

## Usage counters — source of truth

Usage counters live in the Postgres table `usage_counters` with columns
`account_id`, `period` (YYYY-MM), `metric` (`mte`, `seats`, `api_calls`),
`counted_at`, `count`. Postgres is authoritative. This is the outcome of
ADR-0044, adopted after INC-2025-03-08 when a Redis eviction under memory
pressure reset counters mid-month and Ledger re-billed customers on the
next nightly tick.

Redis is still used as a *read-through* cache for the Portal's "usage
this month" widget, but writes go to Postgres first and the Redis key is
invalidated on write. Any doc still claiming Redis is the source of truth
for usage predates March 2025 and is stale; refer to ADR-0044.

Error codes:

| Code       | HTTP | Meaning                                     |
|------------|------|---------------------------------------------|
| `LDG-4001` | 401  | Missing or invalid bearer token             |
| `LDG-4003` | 403  | JWT not authorized for account              |
| `LDG-4402` | 400  | Invalid Stripe signature on webhook         |
| `LDG-4409` | 409  | Concurrent subscription change              |
| `LDG-5010` | 500  | Stripe API 5xx (retried by Stripe)          |

## Nightly invoice cron

At 02:00 UTC a Kubernetes CronJob (`ledger-invoice-nightly`) runs
`python -m ledger.jobs.close_period`. For every account whose current
billing period ends the previous UTC day, it:

1. Freezes the usage counters (writes a `usage_snapshot` row).
2. Calls Stripe to add the metered items to the pending invoice.
3. Advances the account's `next_billing_period_start`.

The job is idempotent per `(account_id, period)`; a re-run after a partial
failure picks up where the last attempt left off. Alerts on the CronJob
failing go to App on-call, secondary to Growth Eng manager.

## Related

- `backend/beacon-service.md` (for how usage data is aggregated for
  display; Ledger only stores the counter, not the raw events).
- `adrs/0044-usage-counters-source-of-truth.md`
- `postmortems/2024-11-14-stripe-double-charge.md`
- `postmortems/2025-03-08-ledger-overbilling.md`
