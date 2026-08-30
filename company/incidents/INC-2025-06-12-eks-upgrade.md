---
title: "INC-2025-06-12: EKS 1.28 → 1.29 upgrade — CoreDNS outage"
category: incident
author: Priya Ramanathan
team: Platform
created: 2025-06-12
updated: 2025-06-14
status: resolved
version: 1.1
---

# INC-2025-06-12 — EKS upgrade outage (CoreDNS drain)

- **Severity:** SEV-1
- **Status:** Resolved
- **Detected:** 2025-06-12 21:04 PT via cascading 5xx alerts
  (`dd:monitor/44902` — `portal.error_rate > 5%`)
- **Resolved:** 2025-06-12 21:51 PT
- **PagerDuty:** PD-INC-E14771
- **Slack channel:** `#inc-2025-06-12`
- **Responders:** Priya Ramanathan (IC), Ben Ortiz (SRE), Marcus J.
  (Platform), Elena Vasquez (Product Eng), Wen Liu (Ingest)

## Summary

Planned EKS control-plane upgrade from 1.28 → 1.29 was executed at 21:00
PT on Thursday (chosen for low traffic). Control plane upgrade completed
cleanly. Node group rolling replacement then began. During the roll,
the CoreDNS Deployment (2 replicas) was drained simultaneously — the
PodDisruptionBudget was set to `maxUnavailable: 1`, and the Deployment
spec had `maxSurge: 0`, so the second replica couldn't come up on a new
node before the first was terminated. For ~47 minutes, cluster-wide
in-cluster DNS resolution was broken.

Effect: Portal, Beacon, Ledger, Compass, and Relay (which resolve each
other via `*.svc.cluster.local`) began returning 5xx. Aurora and Pulse
were partially insulated — Aurora's public path did not depend on
in-cluster DNS for the request handler, though its downstream writes to
Kafka via `b-1.msk-prod.mrdn.io` (external DNS) started failing when
node-local DNS caches expired.

## Impact

- **Portal:** ~100% 5xx from 21:04 – 21:47 PT.
- **Beacon:** ~100% 5xx from 21:06 – 21:47 PT.
- **Aurora ingest:** degraded from 21:18 PT (external DNS resolution
  via node-local cache started failing after cache expiry). Aurora
  returned 502 for ~40% of requests during degraded window. No event
  loss — customer SDKs retried.
- **Estimated affected customers:** all customers with active traffic
  in that window (~380 workspaces).
- **Data loss:** None.
- **SLO impact:** Monthly availability SLO breached for Portal and
  Beacon (99.9% → 99.7% for June).

## Timeline (PT)

- **21:00** — Priya begins `eksctl upgrade cluster --version 1.29`
  per `runbooks/upgrade-eks-cluster.md`. Change ticket CHG-2025-1104.
- **21:02** — Control plane upgrade completes.
- **21:03** — Node group rolling replacement begins (`kubectl drain`
  loop). First node holding a CoreDNS pod is drained.
- **21:03** — Second CoreDNS pod scheduled on new node — but the
  new node is not yet Ready. Pod is Pending. PDB honored (only 1
  unavailable), but the second pod also gets terminated when its
  node is next drained a moment later.
- **21:04** — DNS resolution begins failing cluster-wide.
  `dd:monitor/44902` fires.
- **21:07** — Priya, Ben, Marcus J. join `#inc-2025-06-12`. Declared
  SEV-1 at 21:09.
- **21:14** — Root cause identified as CoreDNS unavailability via
  `kubectl get pods -n kube-system` (0/2 Ready).
- **21:22** — First manual attempt to scale CoreDNS to 6 replicas
  blocked by admission webhook still resolving DNS itself. Circular
  dependency workaround: bypass webhook via
  `--validate=false`.
- **21:35** — CoreDNS scaled to 6 replicas manually; new pods
  pinned to Ready nodes via node selector.
- **21:41** — DNS resolution restored across cluster.
- **21:47** — Portal, Beacon, Ledger error rates normalize.
- **21:51** — Incident closed. Node group rollout paused pending
  postmortem.

## Mitigation

1. CoreDNS manually scaled to 6 replicas.
2. Node group rollout paused; completed the following morning after
   pinning CoreDNS to a stable node subset.
3. EKS upgrade runbook temporarily marked "do not use" pending
   postmortem action items.

## Follow-up

Full postmortem: `postmortems/2025-06-12-eks-upgrade.md`. See
`infrastructure/eks-cluster.md` for the current CoreDNS topology
(dedicated node group, 4 replicas, `maxSurge: 1`).
