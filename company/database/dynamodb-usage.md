---
title: DynamoDB Usage at Meridian
category: database
author: Dara Okonkwo
team: Security
created: 2024-10-08
updated: 2026-03-02
status: current
version: 1.3
---

# DynamoDB Usage

Meridian uses a single DynamoDB table in production. That's it. If you're
thinking of storing something new in DynamoDB, please raise it with the
Platform team first — the current single-table use is deliberate and we'd
like to keep the operational surface small.

## The one table: `gatekeeper-revoked-jwt-ids`

- **Owner:** Security (Gatekeeper service)
- **Region:** us-west-2, on-demand billing
- **Primary key:** `jti` (String) — the JWT ID claim
- **Attributes:**
  - `jti` (String, PK) — matches the `jti` claim of the revoked token
  - `revoked_at` (Number) — unix seconds
  - `reason` (String) — one of `logout`, `admin_revoke`, `rotation`, `incident`
  - `ttl` (Number) — unix seconds at which the item should expire
- **TTL:** enabled on the `ttl` attribute. Items are set to expire ~5 minutes
  after the underlying token's `exp` claim, so the revocation list can't grow
  past the maximum useful window.

Gatekeeper checks this table on every access-token validation. The lookup is
cache-fronted (30s local TTL) and falls open on DDB unavailability — because
if DynamoDB is fully down, refusing every request would take the product
down entirely, and the practical revocation window is already bounded by
the 60-minute access-token TTL.

## Why DynamoDB and not Redis

An earlier iteration (2022–2023) kept the revocation list in Redis for
convenience. That was fine most of the time, but the semantics we actually
want — "if I revoke a token, it stays revoked until it would have expired
anyway" — are much easier to reason about against a durable store than
against `allkeys-lru`. DynamoDB TTL is the exact primitive we want:
durable, cheap, and self-cleaning.

We considered Postgres too, but the write pattern (bursty on incident
response, otherwise near-zero) fits on-demand DynamoDB pricing far better
than a provisioned RDS instance we'd have to size for the peak.

## Access

- Writers: Gatekeeper only.
- Readers: Gatekeeper only. Portal and Beacon do not touch this table;
  they call Gatekeeper's gRPC `Authorize` endpoint (see
  `security/authorization.md`).
- IAM: Gatekeeper's pod role has `dynamodb:GetItem`, `PutItem`, and
  `Query` on this table. No other service.

## Related

- `security/authentication.md`
- `database/redis-usage.md` (why the session store lives in Redis but
  revocation does not)
