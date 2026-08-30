---
title: "ADR-0038: FastAPI is the standard framework for new Python services"
category: adr
author: Marcus Oduya
team: Engineering
created: 2024-05-02
updated: 2024-05-14
status: Accepted
version: 1.0
---

# ADR-0038: FastAPI is the standard framework for new Python services

## Context

We have a mix of Python HTTP frameworks in production:

- Django (legacy monolith, mostly retired but Compass earlier used Django)
- Flask (2021-era services: original Ledger, original Beacon)
- FastAPI (adopted piecemeal starting 2022 during the Django → smaller
  services rewrite)

New services keep re-litigating the "which framework" question in design
reviews. We want a default.

## Decision

**FastAPI (Python 3.11)** is the default for all new Python HTTP services.
Existing Flask services should migrate opportunistically when they have a
major refactor; there is no hard deadline. Django is on the tech-radar Hold
list; do not start new Django services.

Standard project template lives in `meridian/service-template-python` and
includes:

- FastAPI + uvicorn (production runner: gunicorn with uvicorn workers)
- Pydantic v2 models for request/response
- SQLAlchemy 2.0 (async) for Postgres
- `httpx` async client for outbound HTTP
- Pytest + pytest-asyncio
- Structured logging via `structlog` → Datadog

## Alternatives considered

- **Stay Flask-only.** Familiar but sync-only story is now a real
  bottleneck for services doing lots of I/O (Beacon fans out to
  Beacon-Aggregator, then ClickHouse).
- **Litestar / Starlette directly.** Litestar is compelling but the
  ecosystem is smaller. Starlette-direct means reimplementing DI, docs,
  validation we get for free in FastAPI.
- **Rewrite everything in Go.** Discussed and rejected — Go stays the
  choice for perf-critical services (Aurora, Pulse, Gatekeeper, Relay,
  Cartograph), Python stays the choice for business-logic services
  (Beacon, Ledger, Compass). See `engineering/language-choices.md`.

## Consequences

**Positive:**
- Async I/O, automatic OpenAPI docs, Pydantic type checking at the edge.
- One template, one set of libraries, one story for onboarding.

**Negative:**
- Existing Flask code paths remain (Ledger has a Flask blueprint for the
  Stripe webhook that's older than 2023 — untouched until we have a
  reason to change it).
- Async SQLAlchemy has sharper edges than sync; new hires often trip.

## Status

Accepted 2024-05-14.
