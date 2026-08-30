---
title: Meridian Data — Company Overview
category: overview
author: Sam Whitfield
team: Product
created: 2024-02-10
updated: 2026-08-14
status: current
version: 4.1
---

# Meridian Data

Meridian Data, Inc. builds **Meridian**, a real-time analytics platform for
mid-market e-commerce companies. We help merchants understand what's happening
on their storefronts as it happens — clickstream, orders, funnel drop-off,
cohort behavior, and attribution — without having to stand up a data team.

## Who we serve

Our sweet spot is Shopify Plus-tier merchants doing roughly $10M to $500M in
annual GMV. As of August 2026 we have around **430 paying customers**, including
Buoyant Apparel, Kettle & Kiln, Forge Athletics, Nordwind Cycles, and HausGoods.
We launched an **Enterprise tier** in 2025, which added SSO/SAML (via WorkOS)
and higher-volume commitments.

## What the product does

Customers send us events (page views, add-to-carts, orders, custom events)
through our ingest API (**Aurora**), we enrich and store them in ClickHouse,
and they query through dashboards in **Portal** or via our public **v3 API**
(powered by **Beacon**). Common use cases:

- Real-time dashboards for merchandising and marketing teams
- Cohort and funnel analysis
- Multi-touch attribution (v1 today, v2 shipping Q4)
- Alerts on business metrics (via Lighthouse)
- Outbound webhooks into customer systems (via Relay)

## Company at a glance

- **Founded:** March 2019 in Seattle by Nadia Chen (CEO) and Ravi Patel (CTO)
- **HQ:** Seattle, Pioneer Square. Remote-friendly. Small London hub since 2024.
- **Headcount (Aug 2026):** 112 (Engineering: 58)
- **Funding:** Series B, $45M led by IVP (2024). Total raised: ~$66.5M.
- **Pricing:** Starter / Growth / Scale / Enterprise, metered on
  **monthly tracked events (MTEs)**.

## Where we run

Primary region is **us-west-2** (Oregon), with warm-standby DR in **us-east-1**
for Postgres and S3 replication. Our **EU region** in Frankfurt (eu-central-1)
is in build-out this quarter — see the EU kickoff notes for detail. We run
on EKS (Kubernetes 1.29), deployed via ArgoCD from GitHub.

## How we work

Engineering is organized around services rather than layers. Teams own their
services end-to-end, including on-call. We have two on-call rotations —
**App** and **Platform** — with weekly Monday handoffs. Blameless postmortems
are the norm; the incident and ADR archives are considered required reading
for anyone touching production.

## Where to go next

- New engineer? Start at `onboarding/eng-onboarding-day-1.md`.
- Curious how we got here? `history.md`.
- Wondering who owns what? `leadership.md` and the team list in `_CANON.md`.
