---
title: Service Map
category: architecture
author: Ben Ortiz
team: SRE
created: 2024-03-01
updated: 2026-07-01
status: current
version: 3.1
---

# Service Map

Who calls whom. Ownership lives in
`engineering/service-ownership.md`; this doc is only about the edges
between services. Canonical names throughout.

## Legend

- **sync** — synchronous request/response (HTTP or gRPC).
- **async** — fire-and-forget across Kafka, SQS, or Redis Streams.
- **cache-check** — sync call, but a miss is not an error.

## Edges

| Caller | Callee | Type | Purpose |
|--------|--------|------|---------|
| Portal | Beacon | sync | Dashboard queries |
| Portal | Ledger | sync | Billing UI (plans, invoices, usage) |
| Portal | Compass | sync | Signup, workspace bootstrap |
| Portal | Gatekeeper | sync | Login, token refresh, SSO redirect |
| SDK (customer) | Aurora | sync | Event ingest (`POST /v3/track`) |
| SDK (customer) | Beacon | sync | Public read API for programmatic use |
| Aurora | Gatekeeper | sync | Validate + cache workspace write key |
| Aurora | Cartograph | sync | Validate event against workspace schema |
| Aurora | Kafka `events.raw` | async | Publish accepted events |
| Aurora | Kafka `events.dlq` | async | Rejected events for later inspection |
| Pulse (enrich) | Kafka `events.raw` | async | Consume raw events |
| Pulse (enrich) | Kafka `events.enriched` | async | Publish enriched events |
| Pulse (enrich) | Postgres | cache-check | Pull cohort tag definitions |
| Pulse (writer) | Kafka `events.enriched` | async | Consume for ClickHouse write |
| Pulse (writer) | ClickHouse | sync | Batch insert `events_local` |
| Pulse (writer) | S3 `meridian-events-archive` | async | Overflow buffer when CH degraded |
| Beacon | Gatekeeper | sync | Validate JWT, resolve workspace |
| Beacon | Beacon-Aggregator | cache-check | Try precomputed rollup first |
| Beacon | ClickHouse | sync | Slow-path queries |
| Beacon-Aggregator | Redis | cache-check | Hot layer |
| Beacon-Aggregator | Postgres | sync | Warm layer + rollup metadata |
| Beacon-Aggregator | ClickHouse | sync | Rebuild rollups (scheduled) |
| Ledger | Gatekeeper | sync | Auth (admin + customer) |
| Ledger | Postgres | sync | Subscriptions, invoices, usage counters |
| Ledger | Stripe (external) | sync | Charge, subscription CRUD |
| Ledger | Stripe (external) | async | Webhook receiver (`/webhooks/stripe`) |
| Ledger | ClickHouse | sync | Read MTE usage for metered billing |
| Compass | Gatekeeper | sync | Create user, issue first token |
| Compass | Postgres | sync | Create workspace |
| Compass | Cartograph | sync | Seed default event schemas |
| Compass | Atlas | async (SQS) | Kick sample-data seeding job |
| Gatekeeper | Postgres | sync | Users, workspaces, role bindings |
| Gatekeeper | DynamoDB | sync | Session revocation list |
| Gatekeeper | Redis | sync | Rate limits, JWT nonce cache |
| Gatekeeper | WorkOS (external) | sync | SSO/SAML |
| Cartograph | Postgres | sync | Schema definitions |
| Cartograph | Redis | cache-check | Compiled validators |
| Relay | Kafka `events.enriched` | async | Consume for webhook fan-out |
| Relay | Postgres | sync | Webhook subscriptions |
| Relay | Customer endpoint (external) | sync | Deliver webhook (with retry) |
| Lighthouse | ClickHouse | sync | Evaluate alert rules on schedule |
| Lighthouse | Postgres | sync | Alert rule definitions |
| Lighthouse | Postmark (external) | sync | Alert email delivery |
| Atlas | ClickHouse | sync | Nightly export queries |
| Atlas | S3 `meridian-exports` | async | Write export files |
| Atlas | Customer warehouse (external) | sync | Optional reverse-ETL |

## Notable properties

- **Everything authenticated hits Gatekeeper.** That's by design.
  Gatekeeper caches heavily; the p99 is ~4ms.
- **The read path never crosses Kafka.** Only ingest is streamed.
- **The write path never touches Beacon.** Aurora writes; Beacon reads.
  The only edge between them is transitive via ClickHouse.
- **No service calls Portal.** Portal is a terminal — it only makes
  outbound calls.
- **Ledger reads ClickHouse for MTE counts** — this is the one place
  where a Growth Eng service touches the analytics store. It's on a
  read replica.

## Not shown

Observability (Datadog agents), CI/CD (ArgoCD), IaC (Terraform), and
internal admin tools are all off this map — they operate on services,
not through them.
