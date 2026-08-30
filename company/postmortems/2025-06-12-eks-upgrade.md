---
title: "Postmortem: EKS 1.28→1.29 upgrade — CoreDNS outage (2025-06-12)"
category: postmortem
author: Priya Ramanathan
team: Platform
created: 2025-06-27
updated: 2025-07-02
status: current
version: 1.1
---

# Postmortem — 2025-06-12: EKS upgrade CoreDNS outage

> Related incident: `incidents/INC-2025-06-12-eks-upgrade.md`
> Related runbook: `runbooks/upgrade-eks-cluster.md` (rewritten)
> Related infrastructure doc: `infrastructure/eks-cluster.md`
> Blameless. Reviewed by Priya, Ben, Marcus J., Elena.

## Summary

The planned EKS control-plane and node-group upgrade from 1.28 to
1.29 was executed at 21:00 PT on Thursday 2025-06-12. The control
plane upgraded cleanly. During the node-group rolling replacement,
both CoreDNS pods became unavailable simultaneously — the
PodDisruptionBudget allowed `maxUnavailable: 1` but the Deployment
`maxSurge: 0` prevented a replacement pod from starting on a new
node before the old one was terminated. Cluster-wide in-cluster DNS
resolution failed for 47 minutes. Portal and Beacon returned 5xx to
customers for the duration; Aurora degraded once node-local DNS
caches expired. No data was lost.

## Impact

- Portal 5xx: ~100% from 21:04 – 21:47 PT.
- Beacon 5xx: ~100% from 21:06 – 21:47 PT.
- Aurora: ~40% 502 rate from 21:18 – 21:47 PT (external DNS lookups
  to MSK began failing when node-local cache expired).
- Approximate customers affected: ~380 workspaces with active
  traffic in the window.
- Data loss: none. Aurora SDKs retried; events landed in Kafka
  after DNS recovery.
- Monthly SLO: Portal + Beacon breached 99.9% target for June
  (fell to 99.7%).

## Timeline (PT)

- **21:00** — `eksctl upgrade cluster --version 1.29` initiated.
  CHG-2025-1104.
- **21:02** — Control plane at 1.29.
- **21:03** — Node group `ng-services-1` begins rolling replacement.
  Node holding one of the two CoreDNS pods is drained.
- **21:03 (a moment later)** — Second CoreDNS pod scheduled on a
  new node that is not yet `Ready`. Pod is `Pending`. In parallel,
  the next node in the roll (which happens to host the surviving
  CoreDNS pod) begins draining. PDB allows it because "only 1
  unavailable" is technically satisfied when the pending pod is
  counted as available.
- **21:04** — Both CoreDNS pods effectively unavailable. Cluster
  DNS resolution starts failing.
  `dd:monitor/44902` (`portal.error_rate > 5%`) fires.
- **21:07** — Priya, Ben, Marcus J. join `#inc-2025-06-12`.
- **21:09** — SEV-1 declared.
- **21:14** — Root cause identified: 0/2 CoreDNS Ready.
- **21:22** — First attempt to `kubectl scale deploy/coredns -n
  kube-system --replicas=6` blocked by admission webhook that
  itself required DNS to reach its API server. Workaround: apply
  with `--validate=false`.
- **21:35** — CoreDNS scaled to 6 replicas manually, pinned via
  node selector to nodes already `Ready` on 1.28.
- **21:41** — DNS resolution restored cluster-wide.
- **21:47** — Portal / Beacon / Ledger error rates return to
  baseline.
- **21:51** — Incident closed. Node group rollout paused.

## Root cause

The CoreDNS Deployment had:

- `replicas: 2`
- `strategy.rollingUpdate.maxSurge: 0`
- `strategy.rollingUpdate.maxUnavailable: 1`
- `PodDisruptionBudget: maxUnavailable: 1`

With `maxSurge: 0`, no replacement pod can start on a new node
until an old one has been terminated. With only 2 replicas and a
PDB allowing 1 unavailable, node draining could — and did — take
the pod count to 0 Ready during a coincident drain window. The
scheduler couldn't get a replacement running fast enough because
new nodes were still becoming `Ready` as part of the roll.

The upgrade runbook did not require pre-checking CoreDNS PDB and
Deployment strategy against the number of concurrent node drains.

## Contributing factors

- **CoreDNS ran on the general-purpose node group.** So it
  competed for capacity with everything else during a rolling
  replacement, and its scheduling depended on the same node pool
  that was actively being churned.
- **Only 2 CoreDNS replicas.** This was the AWS/EKS default at the
  time. For our traffic it was under-provisioned.
- **No dedicated node pool for `kube-system` critical components.**
- **The admission webhook depended on cluster DNS.** So the
  "obvious" mitigation (scale CoreDNS up) was itself blocked by
  the outage, costing us ~10 minutes.
- **The upgrade runbook was silent on CoreDNS.** It focused on
  workload readiness and control-plane version.
- **No synthetic DNS probe.** Nothing was continuously testing
  in-cluster `nslookup redis.svc.cluster.local`; our first signal
  was application 5xx.
- **Time-of-day decision.** 21:00 PT was low traffic in the US but
  active in Europe. We had ~40 European customers online.

## What went well

- Detection was near-immediate once DNS broke — Datadog fired
  within a minute.
- Team assembly was fast. Priya, Ben, Marcus J. were all in
  `#inc-2025-06-12` within 3 minutes of the page.
- The `--validate=false` workaround was found and applied without
  panic; the team recognized the circular dependency quickly.
- No customer data was lost. Event replay after recovery was
  clean.
- Post-incident, the node group rollout was NOT force-completed
  overnight. The team paused, wrote the postmortem outline the
  next morning, and completed the roll with the CoreDNS
  mitigations in place.

## What went poorly

- The upgrade was executed against a cluster whose CoreDNS
  topology was not upgrade-safe, and no automated check would have
  caught it.
- We had rehearsed control-plane upgrades against staging but not
  the specific node-group rolling scenario at production density.
  Staging had 2 CoreDNS replicas as well, but its node group is
  smaller and the drain never coincided with both replicas.
- No customer comms were sent during the incident. Customers found
  out via broken dashboards. A brief status-page post at 21:15 PT
  would have helped.
- We had no synthetic in-cluster DNS probe.

## Action items

| # | Owner | Description | Status | Due |
|---|-------|-------------|--------|-----|
| 1 | Marcus J. | **CoreDNS on dedicated node group.** New `ng-system` with taints, `topologySpreadConstraints` across 3 AZs, 4 replicas, `maxSurge: 1`, `maxUnavailable: 0`. Not co-scheduled with application workloads. | done | 2025-07-10 |
| 2 | Priya | **Upgrade runbook rewrite.** `runbooks/upgrade-eks-cluster.md` now requires a 30-minute pre-upgrade smoke test in staging with matching workload profile; CoreDNS PDB + strategy pre-check; explicit staged node-group roll with pause between waves. | done | 2025-07-15 |
| 3 | Ben | **Synthetic DNS probes.** Datadog synthetic tests running from inside the cluster resolving `redis.svc.cluster.local`, `postgres.svc.cluster.local`, `kafka-b1.mrdn.io` every 30s. `dd:monitor/45501`. | done | 2025-06-30 |
| 4 | Priya | Upgrade rehearsal drill in staging against a production-density workload replica, quarterly. First run 2025-Q3. | recurring | 2025-Q3 first pass |
| 5 | Ben / Lin | Status-page comms template for infra incidents; on-call playbook updated to publish within 10 minutes of SEV-1. | done | 2025-07-08 |
| 6 | Marcus J. | Node-local DNS cache (`node-local-dns`) evaluated and deployed. Reduces blast radius of any future CoreDNS incident. | done | 2025-08-04 |

## References

- `infrastructure/eks-cluster.md` — current topology, including the
  dedicated `ng-system` node group and CoreDNS configuration.
- `runbooks/upgrade-eks-cluster.md` — rewritten runbook.
- `runbooks/kubernetes-dns-troubleshooting.md` — new, based on the
  `--validate=false` workaround and node-local DNS behavior.
