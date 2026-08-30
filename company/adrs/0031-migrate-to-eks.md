---
title: "ADR-0031: Migrate from ECS to EKS"
category: adr
author: Priya Ramanathan
team: Platform
created: 2024-01-08
updated: 2024-03-25
status: Accepted
version: 1.2
---

# ADR-0031: Migrate from ECS to EKS

## Context

We currently run all long-lived services on ECS Fargate (Aurora, Beacon,
Ledger, Compass, Gatekeeper, Portal, Relay). Batch jobs run on ECS EC2
with a shared cluster. ClickHouse runs on standalone EC2 outside ECS.

Pain points as of Q4 2023:

- **Task-definition sprawl.** ~180 active task definitions, no reasonable
  local diff between environments.
- **Poor traffic-shaping.** Rolling updates in ECS don't give us the
  canary + traffic-split control we want as we push toward SEV budgets.
- **Tooling gap.** Datadog, ArgoCD, Karpenter, and the k8s-native things
  we want to adopt (see also ADR-0038, coming) are all clearly better
  supported on Kubernetes.
- **Networking.** ECS service discovery via Cloud Map is workable but
  every new inter-service call is a config chore.
- **Data-plane parity.** ClickHouse operators (Altinity) and Karpenter
  fit well in EKS and would let us bring ClickHouse under a single
  orchestration story.

## Decision

Migrate all workloads to a managed EKS cluster (`meridian-prod-usw2`) on
Kubernetes 1.28. Cutover services incrementally with a hard-cutover date
of **2024-03-18** for public-facing services. Retire ECS Fargate by
2024-Q3.

Deployment: introduce ArgoCD for continuous delivery, replacing our
Jenkins → `deploy-prod.sh` pipeline. See separate ADR (draft) for CD
tooling.

## Alternatives considered

- **Stay on ECS.** Cheapest option, but the tooling gap gets wider every
  quarter. Rejected.
- **Migrate to EKS + AWS App Mesh.** Considered for observability; App Mesh
  roadmap is uncertain, we prefer sticking with Kubernetes-native
  primitives + Datadog APM.
- **HashiCorp Nomad.** Considered briefly (small ops footprint) but
  ecosystem is much smaller.

## Consequences

**Positive:**
- Common tooling for services + data plane.
- Better traffic-shaping (Argo Rollouts) supports our progressive delivery
  goals.
- Karpenter for autoscaling wins on both cost and speed.

**Negative:**
- Bigger learning curve; SRE and every service team must be k8s-literate.
- Upgrade cadence is a real operational burden — the k8s 1.28→1.29
  upgrade in 2025 caused a SEV-1
  (see [INC-2025-06-12](../incidents/INC-2025-06-12-eks-upgrade.md)).
- Higher baseline cost (~+8% for control plane + node overhead).

## Follow-ups

- Deployment ADR (Jenkins → GitHub Actions + ArgoCD).
- ClickHouse-on-EKS migration (finished 2024-Q4).
- CoreDNS on dedicated node group (added after INC-2025-06-12).

## Status

Accepted 2024-01-15. Migration completed 2024-03-18 (services), 2024-Q4
(ClickHouse). ECS decommissioned 2024-08.
