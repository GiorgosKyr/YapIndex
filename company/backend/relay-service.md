---
title: Relay — Outbound Webhooks
category: backend
author: elena.vasquez@meridiandata.io
team: Product Eng
created: 2024-01-19
updated: 2026-07-02
status: current
version: 1.7
---

# Relay

Relay is Meridian's outbound webhook delivery service. Customers subscribe
to internal event types — most commonly `report.generated` and
`alert.fired` — and Relay POSTs a signed JSON payload to their endpoint.
If the delivery fails, Relay retries with exponential backoff and surfaces
the failure in Portal.

In `relay-svc` source code, "webhook" and "subscription" are used
interchangeably; the Postgres table is `webhook_subscriptions` but the API
uses `/subscriptions` for the customer-facing route because that's what
`@meridian/sdk` shipped with. Both names refer to the same thing.

## Runtime

- **Language:** Go 1.22
- **Deployment:** EKS (us-west-2), 3-pod baseline, HPA to 20 on queue depth.
- **Owner:** Product Eng (Elena Vasquez).

## Supported event types

| Event type            | Emitted by      | Notes                                  |
|-----------------------|-----------------|----------------------------------------|
| `report.generated`    | Beacon          | Fires after a scheduled report runs.   |
| `report.failed`       | Beacon          |                                        |
| `alert.fired`         | Lighthouse      | Threshold or anomaly alert.            |
| `alert.resolved`      | Lighthouse      |                                        |
| `cohort.recomputed`   | Beacon          | After a materialized cohort refreshes. |
| `workspace.suspended` | Ledger          | Payment failure state machine.         |
| `workspace.reactivated` | Ledger        |                                        |

The producers publish onto Kafka `webhook.dispatch` and Relay is the sole
consumer.

## Delivery

Each delivery attempt:

1. Look up the subscription's target URL and per-subscription secret from
   Postgres `webhook_subscriptions` (cached in Redis for 60s).
2. Build the payload envelope:

   ```json
   {
     "id": "wh_01HZ7...",
     "workspace_id": "ws_2fT...",
     "type": "alert.fired",
     "occurred_at": "2026-08-30T12:04:11.203Z",
     "data": { ... }
   }
   ```

3. Compute an HMAC-SHA256 over the raw body using the subscription's secret,
   hex-encode it, and send as:

   ```
   X-Meridian-Signature: sha256=<hex>
   X-Meridian-Delivery: wh_01HZ7...
   X-Meridian-Event: alert.fired
   ```

4. POST with a 10-second connect timeout and 20-second read timeout.

Signing (Go):

```go
mac := hmac.New(sha256.New, []byte(sub.Secret))
mac.Write(body)
sig := hex.EncodeToString(mac.Sum(nil))
req.Header.Set("X-Meridian-Signature", "sha256="+sig)
```

A response of 2xx is a success. Anything else (including timeouts,
connection resets, TLS errors, and 4xx from the customer) is a failure.
Note: 4xx is treated as retryable because a lot of customer endpoints
return misleading 4xx status codes during their own deploys.

## Retries

Failed deliveries are retried up to **5 times** with exponential backoff and
jitter: 30s, 2m, 10m, 1h, 6h. After the 5th failure the delivery is marked
`abandoned`. The subscription itself is auto-disabled if a subscription
accumulates 100 consecutive abandoned deliveries; the workspace owner gets
a Postmark email.

Error codes surfaced in the Portal delivery log:

| Code       | Meaning                                                |
|------------|--------------------------------------------------------|
| `RLY-4004` | Subscription URL is not resolvable (DNS failure)       |
| `RLY-4007` | Response body exceeded 1 MB (truncated in log)         |
| `RLY-4008` | TLS handshake failed                                   |
| `RLY-4029` | Customer endpoint returned 429 (backoff extended)      |
| `RLY-5000` | Customer endpoint returned 5xx                         |
| `RLY-5504` | Customer endpoint exceeded read timeout                |

## Portal visibility

Every attempt writes a row to `webhook_delivery_attempts` (Postgres,
partitioned by month, 30-day retention). Portal reads these via a
Beacon-adjacent read endpoint on Relay itself
(`GET /v3/subscriptions/{id}/deliveries?cursor=...`). Customers can click
into a delivery to see the request headers, redacted body, response status,
and response body (first 8 KB).

## Related

- `backend/beacon-service.md` — `report.generated` producer.
- `backend/ledger-service.md` — `workspace.suspended` producer.
- `frontend/portal-overview.md` — the Webhooks settings page.
