---
title: Beacon — Read / Query API
category: backend
author: elena.vasquez@meridiandata.io
team: Product Eng
created: 2022-11-08
updated: 2026-08-05
status: current
version: 4.2
---

# Beacon

Beacon is the read API that powers everything the customer sees in the
Portal — dashboards, cohort views, alert previews, ad-hoc queries. If Portal
is showing a number, Beacon computed it (usually via Beacon-Aggregator).

Historically this was called "Prism" in the pre-launch design docs. A few
ADRs still use that name; they mean Beacon.

## Runtime

- **Language:** Python 3.11
- **Framework:** FastAPI + Uvicorn workers, Gunicorn supervisor.
- **Deployment:** EKS (us-west-2), 8-pod baseline, HPA to 32 on request
  concurrency.
- **Owner:** Product Eng (Elena Vasquez).

## Endpoints (v3)

```
GET  /v3/metrics/{metric_name}         # predefined metric, ?workspace_id=&range=
POST /v3/queries                       # arbitrary aggregation (JSON query DSL)
GET  /v3/cohorts/{id}                  # materialized cohort membership + stats
GET  /v3/cohorts/{id}/members          # paginated (cursor)
GET  /v3/reports/{id}                  # saved report definition + last-run data
POST /v3/reports/{id}:run              # force a fresh run (bypasses agg cache)
GET  /healthz
GET  /readyz
```

Every endpoint requires an `Authorization: Bearer <jwt>` header issued by
Gatekeeper. The workspace is resolved from the JWT's `workspace_id` claim.
For service-to-service traffic (Portal SSR, Lighthouse, Relay), a
service-account JWT with an `on_behalf_of` claim is required.

Example FastAPI route:

```python
@router.post("/v3/queries", response_model=QueryResponse)
async def run_query(
    body: QueryRequest,
    ctx: RequestContext = Depends(auth.workspace_context),
    agg: BeaconAggregator = Depends(deps.aggregator),
) -> QueryResponse:
    cache_hit = await agg.try_serve(ctx.workspace_id, body)
    if cache_hit is not None:
        return cache_hit
    return await clickhouse.execute_query(ctx.workspace_id, body)
```

## Data path

For every request, Beacon:

1. Resolves the workspace and permission scope from the JWT.
2. Asks **Beacon-Aggregator** first. Aggregator checks Redis for a
   query-shape cache hit and, failing that, looks in the Postgres
   `rollups_hourly` / `rollups_daily` tables. See `backend/beacon-caching.md`
   for the full key schema.
3. If aggregator misses (or the query requires row-level granularity),
   Beacon falls back to ClickHouse (`clickhouse-prod` distributed
   `events` table).

Only about 12% of `/v3/queries` traffic reaches ClickHouse in a healthy
week; the other 88% is served from aggregator.

## Query timeouts

The ClickHouse read timeout is **30 seconds** (`clickhouse.settings.max_execution_time=30`,
plus a 32s asyncio wait wrapping the driver call). This was raised from 10s
after INC-2025-09-30, when cohort endpoints returned 500s because slow
queries piled up on the upstream connection pool without ever being killed.
The postmortem also added the pool-exhaustion guard: Beacon now caps
in-flight ClickHouse queries per pod at 16 and returns `BCN-5031` (503) if
that ceiling is hit, rather than letting the pool queue grow unbounded.

Error codes:

| Code       | HTTP | Meaning                                          |
|------------|------|--------------------------------------------------|
| `BCN-4001` | 401  | Missing or invalid bearer token                  |
| `BCN-4003` | 403  | JWT scope does not cover requested workspace     |
| `BCN-4004` | 404  | Cohort / report id unknown to this workspace     |
| `BCN-4400` | 400  | Query DSL parse error                            |
| `BCN-4408` | 408  | Query exceeded 30s ClickHouse timeout            |
| `BCN-5003` | 500  | Upstream ClickHouse error (retryable)            |
| `BCN-5031` | 503  | In-flight query pool saturated (backpressure)    |

## Notable design choices

- The query DSL is **not** SQL. Customers send a structured JSON body
  (`metric`, `filters`, `group_by`, `time_range`, `interval`), and Beacon
  compiles it to a ClickHouse query server-side. This is what lets us
  reroute against aggregator caches transparently.
- All timestamps in requests and responses are ISO-8601 UTC. This was
  enforced starting with API v3 (2025-05-20) — v2 accepted Unix ms too.
- Pagination is cursor-based (base64 of last row PK). No offsets.

See also: `backend/beacon-caching.md`, `backend/cartograph.md`,
`incidents/INC-2025-09-30-beacon-cohort-500s.md`,
`postmortems/2025-09-30-beacon-cohort-500s.md`.
