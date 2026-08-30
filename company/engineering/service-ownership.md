---
title: Service Ownership
category: engineering
author: Ben Ortiz
team: SRE
created: 2024-04-02
updated: 2026-08-12
status: current
version: 4.3
---

# Service Ownership

Who owns what, who gets paged, and where to ask. This is the file that
should be consulted when you don't know who to bother. If this file and
`CODEOWNERS` disagree, this file wins and `CODEOWNERS` needs a PR.

The list of services and their aliases is canonical here — but the
architecture-side view (what each service does, how they connect) lives
in `architecture/system-overview.md` and `architecture/service-map.md`.

## Ownership table

| Service | Aliases | Owning team | Primary on-call | Slack |
|---------|---------|-------------|-----------------|-------|
| Aurora | ingest-api, events-api, `aurora-ingest` | **Ingest team** | Platform on-call | `#svc-aurora` |
| Pulse | stream-processor, `pulse-worker` | Ingest | Platform on-call | `#svc-pulse` |
| Beacon | query-api, metrics-api | Product Eng | App on-call | `#svc-beacon` |
| Beacon-Aggregator | agg, `beacon-agg` | Product Eng | App on-call | `#svc-beacon` |
| Portal | dashboard, web-app | Product Eng | App on-call | `#svc-portal` |
| Ledger | billing-service, `ledger-api` | Growth Eng | App on-call | `#svc-ledger` |
| Compass | onboarding-service | Growth Eng | App on-call | `#svc-compass` |
| Gatekeeper | auth-service, `gk` | Security | App on-call | `#svc-gatekeeper` |
| Cartograph | schema-service | Data | Platform on-call | `#svc-cartograph` |
| Atlas | etl-worker, warehouse-loader | Data | Platform on-call | `#svc-atlas` |
| Lighthouse | alerts | Product Eng | App on-call | `#svc-lighthouse` |
| Relay | webhook-service | Product Eng | App on-call | `#svc-relay` |

The two rotations (`App on-call` and `Platform on-call`) are defined in
PagerDuty and rotate weekly at Monday 10:00 PT. Escalation is
primary → secondary → engineering manager on duty, 5 min per step.

## Team leads (for anything non-page-worthy)

- **Ingest** — Wen Liu
- **Platform** — Priya Ramanathan
- **Data** — Jae-won Park
- **Product Eng** — Elena Vasquez
- **Growth Eng** — Tomás Herrera
- **Security** — Dara Okonkwo
- **SRE** — Ben Ortiz

## Shared infra ownership

Some things are not a service but still need an owner:

| Thing | Owner |
|-------|-------|
| EKS cluster (`prod-uw2`) | Platform |
| Kafka (MSK) | Ingest (day-to-day), Platform (infra) |
| ClickHouse cluster | Data |
| Postgres (RDS `meridian-prod-primary`) | Platform |
| Redis (ElastiCache) | Team that provisioned the namespace; contact SRE if unclear |
| Terraform root modules | Platform |
| `platform/*` shared libs | Platform |
| `@meridian/ui` | Product Eng |
| `@meridian/sdk` (public TS SDK) | Product Eng |

## Ownership handoffs

If a service moves teams:

1. Update this file **first** (PR into `company/engineering/`).
2. Update `CODEOWNERS` in the service repo.
3. Update PagerDuty rotation.
4. Announce in `#eng-announce`.
5. Update the Datadog service tags (`owner:<team>`).

New services must be listed here before their first prod deploy — the
ArgoCD app-of-apps webhook checks for a matching row.

## Multi-tenant note

A handful of services (Beacon, Beacon-Aggregator, Ledger) shard state by
tenant. If you're paged for a "hot tenant" issue, the Datadog dashboard
`Per-Tenant Load` is the first stop before waking the owning team.

---

### Note on Aurora ownership (please read before "correcting" this doc)

The 2023 org chart document (`docs/org/2023-org-chart.md`) still lists
Aurora under **Platform**. That's stale — ownership moved to the
**Ingest sub-team** when it was formed in 2024, and this file reflects
the current state. Do not open a PR to switch Aurora back to Platform
based on the org chart; instead, update the org chart.

Historically, the Data team's FY25 budget document also carried Aurora
under "warehouse ingest" for cost-allocation reasons — that was a
finance grouping, never an engineering one. Any question of "who runs
Aurora" today is answered by this file.
