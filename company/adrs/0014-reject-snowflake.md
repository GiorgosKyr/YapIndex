---
title: "ADR-0014: Reject Snowflake for customer-facing analytics"
category: adr
author: Jae-won Park
team: Data
created: 2022-02-18
updated: 2022-02-25
status: current
version: 1.0
---

# ADR-0014: Reject Snowflake for customer-facing analytics

## Status

**Accepted** — 2022-02-25. The vendor (Snowflake) is rejected for the
current problem. Signed off by Ravi Patel (CTO) and Jae-won Park (Head of
Data).

See ADR-0016 for the chosen replacement (self-hosted ClickHouse).

## Context

Postgres aggregate queries powering Beacon (still called "Prism" in the
codebase at time of writing) are struggling. Customer dashboards frequently
run `GROUP BY` over 30-90 days of event data; queries that used to return
in 200-400 ms are now spiking above 5 s on our largest workspaces.

We piloted **Snowflake** for two weeks with two of our larger customer
workspaces mirrored in.

Observations:

- Query performance was excellent for ad-hoc analyst work, but not for
  the sub-second latency our customer-facing dashboards need. Cold-warehouse
  spin-up added 3-8 s to the first query, and our access pattern (many
  small workspaces, bursty concurrency) defeats warehouse warm-up
  heuristics.
- Cost projection at our forecast Q4-2022 volume: ~$28k/month for the
  workload we would want on Snowflake, dominated by compute-seconds
  rather than storage. This more than doubles our current data-tier
  spend and worsens per-customer unit economics on Starter and Growth
  tiers.
- The consumption pricing model is hard to expose to customers on a
  metered plan.
- Data egress from Snowflake to our Portal API added another network hop
  we did not want.

Snowflake is a very good tool. It is the wrong tool for our specific
constraint: **sub-second latency, high concurrency, small-to-medium
result sets, per-workspace isolation, predictable cost per MTE.**

## Decision

- **Do not adopt Snowflake** for customer-facing analytics.
- Continue evaluating replacements. Shortlist for follow-up ADR:
  - **ClickHouse** (self-hosted) — best fit on paper for our access
    pattern; ops burden is the main concern.
  - **Apache Druid** — strong on real-time ingest but complex, and the
    JVM operational profile is a mismatch for our team.
  - **TimescaleDB** — attractive from a "still Postgres" standpoint;
    less proven at our expected scale for wide `GROUP BY`.
- Snowflake remains a candidate for **internal analytics** (finance,
  product, growth) where latency and cost profile are different. That
  is out of scope here.

## Consequences

Positive:
- Avoids a large recurring cost increase at exactly the time we are
  trying to prove unit economics for Series A follow-on.
- Keeps latency-critical analytics under our operational control.

Negative:
- We remain on Postgres for aggregate queries in the meantime, which is
  not sustainable past Q2 2022. This ADR does not solve the underlying
  problem — it only closes one door.
- Whichever alternative we choose (probably ClickHouse), we take on
  significant new operational surface. Owning a distributed OLAP store
  is a bigger lift than paying Snowflake to run one.

Follow-ups:
- ADR-0016 will document the alternative selection and adoption plan.
- If ClickHouse ops load becomes prohibitive within 12 months, revisit
  managed OLAP options (this may include Snowflake on a different
  pricing tier, or ClickHouse Cloud once GA).
