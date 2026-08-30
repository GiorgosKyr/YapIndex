---
title: Meridian Tech Radar
category: engineering
author: Ravi Patel
team: Engineering
created: 2024-01-15
updated: 2026-06-18
status: current
version: 6.0
---

# Meridian Tech Radar — June 2026

Snapshot of what we build with, what we're trying, and what we're
walking away from. Refreshed roughly every quarter by the CTO with input
from team leads. Movement between quadrants requires an ADR.

Quadrant meanings (ThoughtWorks convention):

- **Adopt** — proven at Meridian, use by default.
- **Trial** — worth using on a real project; keep a close eye on it.
- **Assess** — worth a spike or reading group; not in production.
- **Hold** — do not start anything new with this; existing usage to be
  paid down.

## Adopt

- **Go 1.22** — perf-critical services (Aurora, Pulse, Gatekeeper,
  Relay, Cartograph).
- **Python 3.11 + FastAPI** — business-logic services (Beacon, Ledger,
  Compass, Lighthouse).
- **TypeScript + Next.js 14** — Portal and any new frontend.
- **ClickHouse 24.3** — analytical store, ~6-node self-hosted cluster
  on EKS.
- **PostgreSQL 15 (RDS Multi-AZ)** — OLTP.
- **Redis 7 (ElastiCache)** — cache, rate limiting, session store. Never
  as source-of-truth (see ADR-0044).
- **Kafka (MSK)** — event streaming between Aurora and Pulse.
- **Terraform** — the only sanctioned way to provision AWS infra.
- **ArgoCD** — continuous deployment to EKS.
- **Datadog** — metrics, APM, logs. Sole observability platform since
  2024-Q3.
- **WorkOS** — SSO/SAML/SCIM for Enterprise tier customers.
- **GitHub Actions** — CI (build, test, image push).
- **LaunchDarkly** — feature flags.

## Trial

- **Rust** — one experiment underway in the Insights team (streaming
  anomaly detector prototype). Decision point end of Q4 2026. No new
  Rust adoption elsewhere without a Trial→Adopt ADR.
- **ClickHouse Keeper** — replacement for ZooKeeper in the ClickHouse
  cluster. In staging since May 2026. Production migration scheduled
  Q1 2027 per roadmap.
- **`uv` (Astral)** — Python packaging + resolver. Rolled out to
  Beacon and Ledger in Q1 2026, replacing Poetry. Full rollout
  in progress.
- **OpenTelemetry (traces)** — Datadog is the backend; we're moving
  instrumentation to OTel SDKs on the Python side.

## Assess

- **DuckDB** — being looked at for on-Portal ad-hoc analysis and for a
  future warehouse-connector story. No production use.
- **Pulumi** — alternative to Terraform. Priya has a spike for
  ergonomics-vs-Terraform comparison; report expected end of Q3 2026.
- **pg_vector / pgvector** — for possible in-product search over event
  properties. No product commitment.
- **Temporal** — for durable workflows that today live in a mix of SQS
  + custom retry code inside Ledger and Compass.

## Hold

- **Django** — one legacy code path still exists in Ledger for admin
  screens; being ported to FastAPI. No new Django code, anywhere.
- **New Relic** — retired 2024-Q3 in favor of Datadog. Do not add new
  agents. Some old runbook screenshots still reference NR dashboards;
  those are being replaced.
- **Jenkins** — retired May 2024. If you find a Jenkinsfile still in a
  repo, it is dead code, delete it. All CI is GitHub Actions now.
- **ECS** — migrated off in the March 2024 cutover. Only remaining
  ECS asset is a sandbox account demo; SRE is decommissioning.
- **CoffeeScript** — self-explanatory. One config-generation script
  in the `atlas-jobs` repo still uses it. On Wen's plate.
- **Poetry** — being replaced by `uv`. Do not use on new repos.
- **`identity-service` (name)** — renamed to Gatekeeper in 2023.
  Old references in docs/code should be updated when touched.

## What's not on the radar

Some things people ask about that we've decided against:

- **Snowflake** — evaluated 2022, rejected on cost (ADR-0014). A
  reverse-ETL *connector* is on the 2027 roadmap; that's not the same
  as adopting Snowflake internally.
- **gRPC between internal services** — HTTP+JSON is fine at our
  volume; we spend the perf budget on ClickHouse.
- **GraphQL for Beacon** — considered 2024, dropped. REST + typed SDK
  is easier for the customers who consume us.
