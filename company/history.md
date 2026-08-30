---
title: A short history of Meridian Data
category: overview
author: Ravi Patel
team: Exec
created: 2023-08-01
updated: 2026-06-18
status: current
version: 2.2
---

# A short history of Meridian Data

This is the "how did we get here" doc. It's opinionated, sometimes wrong in
the small details, and roughly accurate in the big ones. If you're new,
read this before the org chart — you'll understand why things are shaped the
way they are.

## 2019 — Two founders and a Django monolith

Nadia and Ravi incorporated Meridian Data in March 2019 in a coworking space
in Pioneer Square. The MVP was a single Django app called `meridian-app` on
one t3.large EC2 instance behind an ELB, with a Postgres RDS. Aggregate
queries hit Postgres directly. It was fine for our first customer, Kettle &
Kiln, who signed in November 2019.

## 2020 — Redis, and the first Real Users

In July 2020 we added Redis for session caching (ADR-0001, though the
original was an informal Google Doc — it was retroactively promoted to an
ADR two years later). By end of 2020 we had ~15 paying customers and were
starting to see slow queries anywhere we asked Postgres to aggregate over
a week of events.

## 2021 — Series A and the Great Extraction

Series A ($18M from Redpoint) closed in April 2021. We grew from 6 to 22
people over the next four months. In August 2021 we did what everyone
internally still calls the **Great Extraction**: the monolith was split
into three services — an ingest service (the ancestor of Aurora), an api
service (which later split again into Beacon and Portal), and a billing
service (which became Ledger). It was scoped as a 6-week project. It took
14 weeks.

## 2022 — ClickHouse, and a rename

By early 2022 the Postgres-backed analytics story was untenable. We
evaluated Snowflake in February and rejected it on cost (ADR-0014).
ClickHouse was adopted for analytics in June 2022 (ADR-0016); the initial
cluster was 4 nodes. The read API that fronted ClickHouse was proposed
under the codename **Prism**; by launch we'd renamed it to Beacon. You'll
still see "Prism" in a few older ADRs.

Late 2022, we rewrote the remaining Django services in FastAPI (Python
3.10, later 3.11). The auth service — which was called `identity-service`
until 2023 — was renamed **Gatekeeper** during this rewrite.

## 2023 — Kafka, and Project Kraken

In March 2023 we introduced Kafka (MSK) between Aurora and ClickHouse.
Before this, Aurora wrote directly to ClickHouse, which was fragile under
load spikes. Pulse was spun up as a Kafka consumer to enrich and write.
See ADR-0022.

Later that year we did **Project Kraken**: the ClickHouse cluster migration
that brought us to a 6-node self-managed cluster on EKS. The codename
"Kraken" belongs specifically to the ClickHouse project, though — as canon
notes — you'll occasionally see people mislabel other 2023–2024 infra work
as Kraken. It isn't.

## 2024 — The March migration and Series B

Q1 2024 was dominated by the **March migration**: cutting over from ECS to
EKS. Cutover happened on **2024-03-18**. It went better than we feared —
one 22-minute Portal outage, no data loss. ADR-0031 covers it.

Right after, we cut Jenkins over to GitHub Actions + ArgoCD (May 2024) and
consolidated observability onto Datadog (Q3 2024), retiring New Relic and
most CloudWatch usage.

August 2024 was the auth-token log-leak incident (INC-2024-08-05).
September, we closed Series B ($45M, led by IVP) and hired Dara as our
first Head of Security. November brought the payment double-charge
incident (INC-2024-11-14) — Ledger's first SEV-1.

## 2025 — Billing scars, v3, and Enterprise

The year had two big scars, both in Ledger.

January 2025: Aurora ingest backup (INC-2025-01-22), Kafka partition skew
after we onboarded a very large customer. This became the seed for our
partition rebalancing runbook.

March 2025: **INC-2025-03-08** — Ledger overbilling because Redis was
authoritative for usage counters and got evicted under memory pressure.
Direct cause of ADR-0044 ("no Redis as source of truth for money"). We
moved usage counters to Postgres over Q2.

May 2025: **API v3 launched (2025-05-20)** with breaking changes vs v2
(cursor pagination, ISO-8601 timestamps, `workspace_id` in body, new error
envelope). Initial v2 EOL was 2026-05-20; extended once already, and
extended again in May 2026 to 2026-11-01.

June 2025: EKS 1.28→1.29 upgrade outage (INC-2025-06-12) — CoreDNS PDB
misconfigured.

November 2025: WorkOS SSO/SAML shipped, Enterprise tier launched.

## 2026 — ClickHouse pain, and the EU

February 2026: ClickHouse OOM during Q4 report generation (INC-2026-02-03).
Atlas was running unbounded selects; we added cost limits shortly after.

May 2026: SSO login outage after WorkOS webhook secret rotation
(INC-2026-05-19).

Q3 2026 (current): EU region buildout in Frankfurt. Not GA yet. Data
residency toggle is being wired into Portal, Compass, and Gatekeeper.

That is where we are, as of June 2026 when this doc was last updated.
