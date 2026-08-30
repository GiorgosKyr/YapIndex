---
title: System Overview
category: architecture
author: Priya Ramanathan
team: Platform
created: 2023-05-04
updated: 2026-07-09
status: current
version: 5.2
---

# System Overview

Meridian is a B2B real-time analytics platform. This doc is the
top-level map — one screen up from the details. For deeper dives see
`data-flow.md`, `service-map.md`, `event-pipeline.md`, and
`portal-architecture.md`. Owned services and their aliases are also
documented in `engineering/service-ownership.md`.

Everything lives in AWS `us-west-2` today. EU (Frankfurt) is planned
for Q3 2026; see `multi-region-plan.md`.

## Request path (high level)

Two distinct request paths run through the platform: **ingest** (SDK →
Meridian) and **read** (customer opens the dashboard).

```
                     ingest path
                     -----------
  Customer app / SDK ──HTTPS──► CloudFront (events.meridiandata.io)
                                     │
                                     ▼
                                   ALB (nlb-ingest-prod)
                                     │
                                     ▼
                                 Aurora  ──► Kafka: events.raw
                                                     │
                                                     ▼
                                                   Pulse (enrichment)
                                                     │
                                                     ▼
                                          Kafka: events.enriched
                                                     │
                                                     ▼
                                                ClickHouse (6-node)


                      read path
                      ---------
  Customer browser ──HTTPS──► CloudFront (app.meridiandata.io)
                                     │
                                     ▼
                                   ALB (alb-portal-prod)
                                     │
                                     ▼
                                  Portal (Next.js SSR + CSR)
                                     │        │
                              (queries)   (billing UI)
                                     │        │
                                     ▼        ▼
                                  Beacon    Ledger
                                     │
                       ┌─────────────┴─────────────┐
                       ▼                           ▼
              Beacon-Aggregator             ClickHouse
              (Redis + Postgres)
```

Not shown for clarity: Gatekeeper (sits in front of every
authenticated call), Cartograph (validates event schemas on ingest),
Relay (pushes outbound webhooks after enrichment), Lighthouse (watches
metric alerts on stored data), Atlas (nightly warehouse exports),
Compass (signup and workspace bootstrap).

## Services in one sentence each

- **Aurora** — public event ingestion HTTP endpoint. Validates, drops
  bad payloads, publishes to Kafka.
- **Pulse** — consumes Kafka, enriches events (geo, UA parsing, cohort
  tags), and batch-writes to ClickHouse.
- **Cartograph** — customer-defined event schemas. Aurora asks
  Cartograph "is this payload valid for this workspace?" on ingest.
- **Beacon** — read/query API. Turns dashboard requests into ClickHouse
  queries.
- **Beacon-Aggregator** — precomputed rollups for common queries;
  Redis-hot, Postgres-warm.
- **Portal** — the customer-facing web app. See `portal-architecture.md`.
- **Ledger** — subscription and invoice management, Stripe integration.
- **Gatekeeper** — AuthN/AuthZ. Issues JWTs, integrates WorkOS for SSO.
- **Compass** — onboarding: signup, workspace provisioning, sample
  data seeding.
- **Relay** — pushes outbound webhooks to customer endpoints after
  enrichment.
- **Lighthouse** — the *product* alerting feature (metric-based alerts
  for customers). Not to be confused with observability alerts, which
  live in Datadog/PagerDuty.
- **Atlas** — nightly ClickHouse → S3 exports and warehouse sync jobs.

## Data stores at a glance

- **Postgres 15 (RDS Multi-AZ)** — workspaces, users, schemas, billing,
  session revocation lists. OLTP only.
- **ClickHouse 24.3 (6-node self-hosted on EKS)** — all event data,
  all analytical queries.
- **Redis 7 (ElastiCache)** — cache, rate limits, aggregator hot layer.
  Never source-of-truth (ADR-0044).
- **DynamoDB** — Gatekeeper session revocation list only.
- **S3** — event archive (`meridian-events-archive`) and exports
  (`meridian-exports`).
- **Kafka (MSK, 12 brokers)** — `events.raw`, `events.enriched`,
  `events.dlq`.

## Infra

- EKS 1.29 in `us-west-2`, migrated from ECS in March 2024.
- Terraform for infra (state in S3, DynamoDB lock).
- ArgoCD for deploys to EKS. GitHub Actions for build/test.
- Datadog for metrics/APM/logs; PagerDuty for alerts.

## What's outside the platform

- **Stripe** for payment processing.
- **WorkOS** for SSO/SAML/SCIM (Enterprise tier).
- **Postmark** transactional email; **Customer.io** marketing.
- **LaunchDarkly** for feature flags.
- **CloudFront** for TLS + edge caching in front of both ingest and app.
