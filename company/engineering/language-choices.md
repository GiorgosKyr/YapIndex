---
title: Language Choices
category: engineering
author: Ravi Patel
team: Engineering
created: 2023-11-08
updated: 2026-04-22
status: current
version: 2.2
---

# Language Choices

Meridian is polyglot on purpose but not by accident. This doc explains
when to reach for which language. See `tech-radar.md` for versions and
`coding-standards.md` for style.

## The three-language rule

We officially support three general-purpose languages for backend and
frontend code:

- **Go** — perf-critical, high-throughput, latency-sensitive.
- **Python** — business logic, integrations, iteration-heavy code.
- **TypeScript** — frontend (Portal) and any JS/TS surface exposed to
  customers (`@meridian/sdk`).

Anything else needs an ADR. The bar is high — the last exception was
Rust for one Insights team experiment.

## When to use Go

Use Go when any of the following is true:

- The service is on the ingest hot path or otherwise sees more than
  ~1k rps sustained.
- p99 latency matters and needs to be under ~50ms.
- The service is mostly IO plumbing with small, well-typed payloads
  (e.g. HTTP → Kafka → HTTP).
- The service needs to run tight against a memory or CPU budget in
  its pod.

Current Go services:

- **Aurora** — event ingest HTTP endpoint. Peak ~14k rps.
- **Pulse** — Kafka consumer + ClickHouse batch writer. Throughput-bound.
- **Gatekeeper** — auth. Every internal request hits it; low-latency
  matters.
- **Relay** — outbound webhooks. Fan-out with retry and backoff.
- **Cartograph** — schema validation on hot ingest path.

## When to use Python

Use Python for services where the code is mostly business rules and the
throughput ceiling is modest (below a few hundred rps per pod):

- Domain rules that change often (Ledger's billing logic, Compass's
  onboarding rules).
- Integrations with third-party SDKs where a Python SDK exists and is
  well maintained (Stripe, WorkOS, LaunchDarkly, S3).
- ETL and batch (Atlas: Airflow + pandas + ClickHouse).
- Query composition and orchestration (Beacon assembles ClickHouse
  queries; the query itself is where the work happens).

Current Python services: Beacon, Beacon-Aggregator, Ledger, Compass,
Atlas, Lighthouse.

We chose FastAPI over Django for new services in 2022 (see
`adrs/0019-fastapi-over-django.md`). Django is on Hold in the tech
radar.

## When to use TypeScript

- Portal (the customer dashboard, Next.js 14).
- Internal admin tools that are web UIs.
- `@meridian/sdk` — the typed API client we ship publicly.
- `@meridian/ui` — the shared design-system components.

Node.js as a backend for services is **not** on the radar. If you find
yourself wanting Node for a backend, that's a signal to reach for
Python or Go.

## Practical guidance for gray zones

- **"It's business logic but it's also on the ingest path."** Go, and
  push the business logic into a config-driven table that Cartograph
  can serve. Aurora should stay dumb.
- **"It's a small internal script."** Python. Put it in
  `platform/scripts/` and don't overthink.
- **"It's a queue consumer."** Go if it's high-throughput or latency
  matters; Python if it's iteration-heavy business logic.
- **"It's a batch job."** Python + Airflow (Atlas). If it's not
  data-warehouse-shaped, ask before adding to Airflow.
- **"It's an ML thing."** Python for now. The Rust experiment in
  Insights is a *specific* streaming case, not a green-light for Rust
  ML services broadly.

## Why not more languages?

Three languages already means three sets of build tooling, three
linters, three test frameworks, and three sets of on-call intuition. We
add a fourth only when the pain of not having it outweighs that. Rust
is being trialed on that basis; the bar for anything else (Elixir,
Kotlin, etc.) is the same.
