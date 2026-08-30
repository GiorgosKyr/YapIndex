---
title: "ADR-0001: Redis (ElastiCache) for session caching"
category: adr
author: Ravi Patel
team: Platform
created: 2020-07-14
updated: 2023-05-02
status: current
version: 1.2
---

# ADR-0001: Redis (ElastiCache) for session caching

## Status

**Accepted** — 2020-07-14. Signed off by Ravi Patel (CTO).

Note (2023-05): The session store for the newly-extracted Gatekeeper
service was moved to Gatekeeper's own dedicated Redis instance during the
Great Extraction follow-up work. The decision here still stands for the
remaining Django code paths that were not yet migrated; those paths were
retired later in 2023 when Gatekeeper became the sole session authority.

## Context

At the time of writing, Meridian runs as a single Django + Postgres
monolith (`meridian-app`) on one EC2 instance, plus an RDS Postgres
Multi-AZ. Django is using the default `django.contrib.sessions.backends.db`
backend, which reads and writes a `django_session` row on every
authenticated request.

Observed problems as we crossed ~40 paying customers:

- The `django_session` table has become the hottest table in the
  database, sitting at ~1.4k writes/sec at peak.
- Postgres CPU is climbing past 60% during business hours, largely from
  session updates.
- p95 request latency has drifted from ~90 ms in early 2020 to ~220 ms
  now, and profiling attributes ~40 ms of that to session read/update.
- Autovacuum on `django_session` runs almost continuously and interferes
  with other write workloads.
- We do not yet have a caching layer of any kind. Adding one would also
  help query result caching later (though that is out of scope for this
  ADR).

We considered:

1. Keep DB sessions, throw hardware at Postgres. Rejected — a scaling
   band-aid that does not remove the fundamental write amplification.
2. Cookie-signed sessions (`signed_cookies` backend). Rejected — we
   already store more than the cookie size budget in the session, and
   invalidation (server-side logout) becomes hard.
3. Memcached (ElastiCache). Considered. Simpler than Redis but no
   persistence or replication story.
4. Redis (ElastiCache). Chosen — see below.

## Decision

Introduce **Redis** as a managed AWS ElastiCache (Redis 5.0) cluster
in `us-west-2`, single primary + one replica for read failover,
initially `cache.m5.large`.

- Use it as the Django session backend
  (`django.contrib.sessions.backends.cache`) with `SESSION_ENGINE`
  pointing at the Redis cache alias `sessions`.
- Session TTL: **24 hours** of inactivity (matches current Postgres
  behavior). Absolute max session lifetime: 30 days.
- Session keys namespaced `sess:<sha256(session_key)>`.
- Redis is not the source of truth for anything else at this time;
  losing the whole cache logs everyone out but does not lose data.

We do not yet use Redis for query caching, rate limiting, or queueing.
Those are anticipated follow-ups but each will get its own ADR.

## Consequences

Positive:

- Removes ~1.4k writes/sec from Postgres, freeing headroom.
- p95 request latency should drop back below 150 ms.
- Gives us a caching primitive we will almost certainly need again soon.

Negative / risks:

- New operational surface: ElastiCache monitoring, failover semantics,
  eviction policy tuning.
- If the Redis primary fails without a clean failover, all authenticated
  users are logged out. Acceptable at current scale; needs revisiting if
  we grow beyond a few hundred concurrent sessions.
- Cost: ~$180/month at the chosen instance size. Trivial.

Follow-ups (not decided here):

- Query result caching for the read-heavy dashboard endpoints (see the
  later `beacon-caching` design).
- Rate limiting on the ingest endpoint (later handled in Redis, ~2023).
- Whether authenticated session state should be in a dedicated cluster
  once we split auth out of the monolith (this later became Gatekeeper
  and got its own Redis).
