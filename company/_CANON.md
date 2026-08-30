# Meridian Data — Internal Canon (authoritative source for all docs)

> This file is the source of truth for names, dates, terminology, incidents,
> and history. Every other document in this knowledge base MUST be consistent
> with this canon in its factual details, unless the doc is intentionally
> *outdated* or *contradictory* (see the "planned inconsistencies" section).

---

## 1. Company

- **Name:** Meridian Data, Inc.
- **Product:** "Meridian" — a B2B real-time analytics platform for mid-market
  e-commerce companies. Ingests clickstream and order events, provides
  dashboards, cohort/funnel analysis, and attribution.
- **Founded:** March 2019 in Seattle by Nadia Chen (CEO) and Ravi Patel (CTO).
- **HQ:** Seattle (Pioneer Square), remote-friendly. Small London hub since 2024.
- **Headcount (Aug 2026):** 112 employees. Engineering: 58.
- **Funding:** Seed (2019, $3.5M), Series A (2021, $18M led by Redpoint),
  Series B (2024, $45M led by IVP).
- **Customers:** ~430 paying customers. Sweet spot: Shopify Plus tier
  ($10M–$500M GMV). Notable logos: Buoyant Apparel, Kettle & Kiln, Forge
  Athletics, Nordwind Cycles, HausGoods. Enterprise tier launched 2025.
- **Pricing tiers:** Starter, Growth, Scale, Enterprise. Metered on
  monthly tracked events (MTEs).

## 2. Leadership & key people

| Role | Name |
|------|------|
| CEO | Nadia Chen |
| CTO | Ravi Patel |
| VP Eng | Marcus Oduya (joined 2023) |
| Head of Platform | Priya Ramanathan |
| Head of Data | Jae-won Park |
| Head of Product Eng | Elena Vasquez |
| Head of Growth Eng | Tomás Herrera |
| Head of Security | Dara Okonkwo (joined 2024-09) |
| Head of Product | Sam Whitfield |
| Head of Support | Lin Zhao |

## 3. Teams

- **Platform** (8 eng) — Kubernetes, Terraform, networking, shared libs. Lead: Priya.
- **Data** (7 eng) — ClickHouse, Kafka, ETL, warehouse. Lead: Jae-won.
- **Product Eng** (12 eng) — Portal (dashboard app), Beacon (query API). Lead: Elena.
- **Growth Eng** (6 eng) — Ledger (billing), Compass (onboarding), Portal billing UI. Lead: Tomás.
- **Ingest** (5 eng) — Aurora, Pulse. Reports into Platform. Lead: Wen Liu.
- **Security** (3 eng) — Gatekeeper, secrets, compliance. Lead: Dara.
- **SRE** (4 eng) — on-call, observability, incident response. Lead: Ben Ortiz.
- **ML/Insights** (3 eng) — experimental. Lead: Priya (interim).

## 4. Services (this is the authoritative list of names)

Every service has a canonical name AND a set of aliases people actually use
in docs, Slack, and code. RAG has to reason about the aliases.

| Canonical | Aliases used in the wild | Purpose | Language | Owner |
|-----------|--------------------------|---------|----------|-------|
| **Aurora** | ingest-api, events-api, `aurora-ingest`, "the ingest" | Public event ingestion HTTP endpoint | Go | Ingest |
| **Pulse** | stream-processor, `pulse-worker`, "the streamer" | Kafka consumer, enrichment, writes to ClickHouse | Go | Ingest |
| **Beacon** | query-api, metrics-api, `beacon-svc` | Read API that powers dashboards | Python (FastAPI) | Product Eng |
| **Portal** | dashboard, web-app, `meridian-portal`, "the app" | React/Next.js customer UI | TypeScript | Product Eng |
| **Ledger** | billing-service, billing-svc, `ledger-api`, "billing" | Subscription & invoice management, Stripe integration | Python (FastAPI) | Growth Eng |
| **Gatekeeper** | auth-service, auth-svc, `gk`, "auth", (legacy: `identity-service`) | AuthN/AuthZ, JWT issuance, SSO | Go | Security |
| **Compass** | onboarding-service, `compass-api` | Signup flow, workspace provisioning, sample data | Python (FastAPI) | Growth Eng |
| **Atlas** | etl-worker, warehouse-loader, `atlas-jobs` | Nightly ClickHouse → S3 exports, warehouse sync | Python (Airflow) | Data |
| **Cartograph** | schema-service, `cartograph-api` | Customer-defined event schemas & validation | Go | Data |
| **Lighthouse** | alerts, `lighthouse-svc` | Internal metric alerting (product feature, NOT observability) | Python | Product Eng |
| **Beacon-Aggregator** | agg, `beacon-agg` | Precomputed rollup cache, backed by Redis + Postgres | Python | Product Eng |
| **Relay** | webhook-service, `relay-svc` | Outbound webhooks to customer endpoints | Go | Product Eng |

**Names that are NOT services (common confusion):**
- "Sentry" is our error monitoring vendor. There is no internal service called
  Sentry. Some early 2022 docs used the codename "Sentry" for what became
  Gatekeeper — those docs are stale.
- "Kraken" was a 2023 codename for the ClickHouse cluster migration project;
  it's not a service.
- "Prism" was a proposed name for Beacon before launch. A few ADRs still use it.

## 5. Tech stack

- **Languages:** Python 3.11 (services), Go 1.22 (perf-critical), TypeScript.
- **Web framework:** FastAPI (Python), chi (Go), Next.js 14 (frontend).
- **Databases:**
  - **PostgreSQL 15** (Aurora RDS, Multi-AZ) — OLTP: workspaces, users, billing, schemas.
  - **ClickHouse 24.3** (self-hosted on EKS, 6-node cluster) — event storage & analytics.
  - **Redis 7** (ElastiCache) — cache, session store, rate limiting, some queues.
  - **DynamoDB** — Gatekeeper session revocation list only.
- **Streaming:** Apache Kafka (MSK), 12 brokers, `events.raw` and `events.enriched` topics.
- **Queues:** SQS for async jobs; Kafka for events; Redis Streams for internal fanout.
- **Object storage:** S3 (`meridian-events-archive`, `meridian-exports`).
- **Search:** OpenSearch (log search only, not customer-facing).
- **Container orchestration:** EKS (Kubernetes 1.29) in us-west-2. Migrated
  from ECS in Q1 2024 (see "March migration" below).
- **IaC:** Terraform (state in S3, DynamoDB lock). Kustomize + Helm for k8s.
- **CI/CD:** GitHub Actions for build+test, ArgoCD for continuous deployment
  to EKS. Prior: Jenkins + custom deploy scripts (retired May 2024).
- **Observability:** Datadog (metrics + APM + logs since 2024-09), Sentry
  (errors), PagerDuty (alerting).  Prior: New Relic + CloudWatch (retired
  2024-Q3).
- **Feature flags:** LaunchDarkly.
- **Payments:** Stripe (primary), Stripe Tax, Stripe Billing.
- **Email:** Postmark (transactional), Customer.io (marketing).
- **SSO / Enterprise auth:** WorkOS (added 2025-Q4).

## 6. AWS layout

- **Primary region:** us-west-2 (Oregon).
- **DR region:** us-east-1 (N. Virginia), warm-standby for Postgres + S3
  cross-region replication only. No active traffic.
- **EU region (planned Q4 2026):** eu-central-1 (Frankfurt). Not live yet.
- **Accounts:** `meridian-prod`, `meridian-staging`, `meridian-dev`,
  `meridian-sandbox`, `meridian-security` (log archive + GuardDuty).
- **VPC CIDRs:** prod 10.20.0.0/16, staging 10.30.0.0/16, dev 10.40.0.0/16.
- **DNS:** `meridiandata.io` (customer-facing), `mrdn.io` (short/internal),
  `meridian.internal` (private zone). Legacy: `getmeridian.com` (still redirects).

## 7. Domain terminology (canonical + aliases)

RAG must handle these aliasings.

| Canonical (product) | Aliases people use |
|---------------------|--------------------|
| **Workspace** | organization, tenant, org, account (in Ledger docs), customer (support docs) |
| **Event** | data point, metric-event, hit (legacy), pings (in some frontend code) |
| **MTE (monthly tracked event)** | tracked event, billable event, MTU (wrong but seen in old sales docs) |
| **Property** | attribute, field, dimension, tag (in Cartograph code) |
| **Cohort** | segment, audience (Growth docs) |
| **Report** | dashboard, view, board (legacy) |
| **API key** | write key, ingest key, token (careful: also means JWT) |
| **Webhook** | callback, subscription (in Relay code) |

## 8. Environments

- `prod` — customer-facing. us-west-2. Deploys via ArgoCD, PR-gated.
- `staging` — full mirror of prod. us-west-2. Deploys on every merge to `main`.
- `dev` — shared dev cluster. Anyone can deploy branches.
- `sandbox` — for demo/sales; reset weekly.

## 9. History (timeline)

- **2019-03**: Founded. Django + Postgres monolith, single EC2, called "meridian-app".
- **2019-11**: First paying customer (Kettle & Kiln).
- **2020-07**: Introduced Redis for session caching. (See ADR-0001, informal.)
- **2021-04**: Series A. Team grows from 6 → 22.
- **2021-08**: **Great Extraction**: monolith split into ingest, api, billing services.
- **2022-02**: Snowflake evaluated for analytics, rejected on cost. ADR-0014.
- **2022-06**: **ClickHouse adopted** for analytics (replaced Postgres aggregate queries). ADR-0016.
- **2022-11**: Django services rewritten in FastAPI (Python 3.10). Legacy `identity-service` renamed to `gatekeeper` in 2023.
- **2023-03**: Kafka (MSK) introduced. Aurora previously wrote directly to ClickHouse; Pulse created to consume from Kafka. ADR-0022.
- **2023-09**: Datadog trialed, not adopted yet (still New Relic).
- **2024-Q1**: **The "March migration"**: ECS → EKS. Cutover on 2024-03-18.
  Datadog adopted as sole observability platform in Q3 2024. ADR-0031.
- **2024-05**: Jenkins → GitHub Actions + ArgoCD. Old deploy runbook obsoleted.
- **2024-08**: Auth token log-leak incident (INC-2024-08-05).
- **2024-09**: Series B. Head of Security hired.
- **2024-11**: Payment double-charge incident (INC-2024-11-14).
- **2025-01**: Aurora ingest queue backup (INC-2025-01-22). Led to Kafka
  partition rebalancing runbook.
- **2025-03**: Ledger Redis eviction bug — customers overbilled (INC-2025-03-08).
  Postmortem drove ADR-0044 (no Redis as source of truth).
- **2025-Q2**: **API v3 released** (2025-05-20). Breaking changes vs v2: cursor
  pagination, ISO-8601 timestamps everywhere, `workspace_id` required in body
  not header, error envelope changed. v2 EOL: 2026-05-20 (extended once).
- **2025-06**: EKS cluster upgrade outage (INC-2025-06-12).
- **2025-11**: WorkOS integration for SSO/SAML (Enterprise tier launch).
- **2026-02**: ClickHouse OOM during Q4 report generation (INC-2026-02-03).
- **2026-05**: v2 API EOL extended (again) to 2026-11-01.
- **2026-Q3 (in progress)**: EU region buildout (Frankfurt), not GA yet.

## 10. Major incidents (short reference — postmortems have detail)

| ID | Date | Title | Severity | Root cause (one-liner) |
|----|------|-------|----------|-------------------------|
| INC-2024-08-05 | 2024-08-05 | Auth tokens leaked in New Relic logs | SEV-2 | Gatekeeper logged full JWT in DEBUG path enabled in prod by mistake. |
| INC-2024-11-14 | 2024-11-14 | Duplicate Stripe charges | SEV-1 | Ledger did not dedupe on Stripe webhook `event.id`; webhook retry caused ~180 double-charges. |
| INC-2025-01-22 | 2025-01-22 | Aurora ingest backlog, 4h data delay | SEV-2 | Kafka partition skew after adding a large customer; single partition became hot. |
| INC-2025-03-08 | 2025-03-08 | Ledger overbilling from stale Redis | SEV-1 | Redis was authoritative for usage counters; eviction under memory pressure caused counter reset, then re-billing on next tick. |
| INC-2025-06-12 | 2025-06-12 | EKS 1.28→1.29 upgrade outage | SEV-1 | CoreDNS pod disruption budget wrong; DNS resolution failed cluster-wide for 47min. |
| INC-2025-09-30 | 2025-09-30 | Beacon 500s on cohort endpoints | SEV-3 | Slow ClickHouse query, no timeout, upstream connection pool exhausted. |
| INC-2026-02-03 | 2026-02-03 | ClickHouse OOM during Q4 exports | SEV-2 | Atlas ran unbounded `SELECT` against clickhouse-prod-3; node OOM-killed. |
| INC-2026-05-19 | 2026-05-19 | Portal login broken for SSO customers | SEV-2 | WorkOS webhook secret rotation not propagated to Gatekeeper. |

## 11. Roadmap (Aug 2026)

- **Q3 2026 (current):** EU region (Frankfurt) — infra buildout underway.
  Data residency toggle in Portal. Compass region routing.
- **Q4 2026:** SCIM provisioning for SSO customers. Attribution v2 (multi-touch).
- **Q1 2027:** ML anomaly detection (Insights team). ClickHouse Keeper migration
  (off ZooKeeper).
- **Q2 2027:** Snowflake connector (reverse ETL).

## 12. On-call

- Two rotations: **App on-call** (Portal, Beacon, Ledger, Gatekeeper, Compass, Relay)
  and **Platform on-call** (Aurora, Pulse, Atlas, Cartograph, infra, k8s).
- Weekly handoff Mondays 10:00 PT.
- Primary + Secondary. PagerDuty. Escalation: 5 min primary → secondary → manager on duty.

## 13. Planned inconsistencies (this is intentional for RAG testing)

The following contradictions/staleness are deliberately baked in. Doc writers
should NOT "fix" them:

1. Old docs still refer to `identity-service` (renamed to Gatekeeper in 2023).
2. Old docs still refer to ECS / Jenkins / New Relic (all deprecated 2024).
3. The `deployment-process.md` runbook exists in TWO versions: a stale one
   in `runbooks/` describing the Jenkins flow (marked deprecated but not
   deleted), and the current one for ArgoCD.
4. Ledger docs sometimes claim Redis is the source of truth for usage
   counters (pre-INC-2025-03-08). Post-incident docs say Postgres is.
5. Terminology inconsistency: "Workspace" vs "Organization" vs "Tenant"
   across teams. Growth docs prefer "organization"; Product Eng uses
   "workspace"; Ledger uses "account" internally.
6. Some docs describe API v2, some v3. A few describe v2 as current.
7. The "who owns Aurora" question has three plausible answers depending on
   the doc: Platform (org chart, old), Ingest (current), Data (billing budget doc).
8. The ClickHouse cluster size is stated as 4 nodes in an old ADR, 6 in canon.
9. Redis was "introduced" for multiple different reasons in different docs:
   - `adrs/0001-*.md`: session caching (the real reason, 2020)
   - `backend/beacon-caching.md`: query result caching (2022, secondary)
   - `runbooks/redis-*.md`: rate limiting (2023)
   All are technically true at different points.
10. The March migration is sometimes described as "ECS to EKS", sometimes
    as "the k8s migration", and one meeting note calls it "Project Kraken"
    (that's actually the ClickHouse project — a common in-house confusion).

## 14. Naming conventions for docs

- ADRs: `adrs/NNNN-kebab-title.md`, e.g. `adrs/0044-usage-counters-source-of-truth.md`.
- Incidents: `incidents/INC-YYYY-MM-DD-slug.md`.
- Postmortems: `postmortems/YYYY-MM-DD-slug.md`.
- Runbooks: `runbooks/verb-noun.md`, e.g. `runbooks/rotate-production-secrets.md`.
- Meeting notes: `meetings/YYYY-MM-DD-topic.md`.

## 15. Frontmatter template

```
---
title:
category:
author:
team:
created:
updated:
status:   # draft | current | deprecated | archived
version:  # semantic-ish, e.g. 1.0, 2.3
---
```
