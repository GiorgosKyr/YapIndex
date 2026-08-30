---
title: EKS Cluster — meridian-prod-usw2
category: infrastructure
author: Priya Ramanathan
team: Platform
created: 2024-03-18
updated: 2026-06-04
status: current
version: 3.0
---

# EKS Cluster: `meridian-prod-usw2`

The production Kubernetes cluster that hosts every Meridian service except
Aurora RDS, MSK, and ElastiCache. Migrated onto EKS in the March 2024
cutover (see ADR-0031). Currently on Kubernetes **1.29** (upgraded from 1.28
after INC-2025-06-12).

## Cluster facts

| Item              | Value                                                        |
|-------------------|--------------------------------------------------------------|
| Name              | `meridian-prod-usw2`                                         |
| Region / AZs      | `us-west-2` / `usw2-az1`, `usw2-az2`, `usw2-az3`             |
| Kubernetes        | 1.29 (control plane on EKS-managed)                          |
| Networking        | AWS VPC CNI (prefix delegation enabled)                      |
| Ingress           | AWS Load Balancer Controller → ALBs per hostname             |
| DNS               | CoreDNS (dedicated node group; see below)                    |
| Autoscaling       | Karpenter (replaced cluster-autoscaler in Q4 2025)           |
| Service mesh      | None (Linkerd was piloted 2025-Q2, not adopted)              |
| Observability     | Datadog Agent DaemonSet, log tailing via Vector              |

The staging cluster is `meridian-stg-usw2`; a lightweight tools cluster
`meridian-tools-usw2` runs Atlantis, ArgoCD, and internal tooling (see
`cicd/argocd-setup.md`).

## Node groups

Karpenter manages all workload capacity via NodePools; the `system` group
stays as a managed node group so the cluster can always cold-start.

| Node group / pool  | Purpose                                | Instance families      | Notes                                    |
|--------------------|----------------------------------------|------------------------|------------------------------------------|
| `system`           | CoreDNS, kube-proxy, aws-node, metrics | `m6i.large`            | Managed NG, min=3 across AZs             |
| `app`              | Portal, Beacon, Ledger, Gatekeeper etc.| `m6i`, `m7i`           | Karpenter, spot=70%                      |
| `ingest-heavy`     | Aurora, Pulse                          | `c6i`, `c7i`           | Karpenter, on-demand only                |
| `clickhouse`       | ClickHouse StatefulSet                 | `r6i.4xlarge`          | Karpenter, on-demand, tainted            |

### CoreDNS node group

After **INC-2025-06-12** (cluster-wide DNS failure during the 1.28→1.29
upgrade), CoreDNS runs on its own dedicated managed node group with a
correctly configured `PodDisruptionBudget` (`minAvailable: 2`, replicas: 3
spread across AZs) and priority class `system-cluster-critical`. Do not
schedule other pods here — the group is tainted
`dedicated=coredns:NoSchedule`.

### ClickHouse pool

The 6-node ClickHouse cluster runs on `r6i.4xlarge` nodes (128 GiB RAM,
16 vCPU). Nodes are tainted `workload=clickhouse:NoSchedule` and the
StatefulSet tolerates it. Local NVMe is not used — data lives on `gp3` EBS
volumes with cross-AZ topology spread. See `data/clickhouse-cluster.md` for
disk sizing.

## Autoscaling (Karpenter)

Karpenter was rolled out in **Q4 2025**, replacing cluster-autoscaler on the
`app` and `ingest-heavy` groups. Example NodePool (trimmed):

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: app
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: [m6i, m7i]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [spot, on-demand]
        - key: topology.kubernetes.io/zone
          operator: In
          values: [us-west-2a, us-west-2b, us-west-2c]
      nodeClassRef:
        name: app-default
  limits:
    cpu: 2000
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

Spot interruption handling is done by Karpenter itself; no separate NTH.

## Common `kubectl` operations

Contexts are named after the cluster; use `kubectx meridian-prod-usw2`
after `aws eks update-kubeconfig --name meridian-prod-usw2`.

```bash
# Who's on-call? Just kidding — but list all pods in the ingest namespace.
kubectl -n ingest get pods -o wide

# Roll a deployment (rare — normally ArgoCD; see cicd/deploy-pipeline.md).
kubectl -n product rollout restart deploy/beacon

# Watch a rollout.
kubectl -n product rollout status deploy/beacon --timeout=5m

# Drain a node before manual replacement.
kubectl drain ip-10-20-42-17.us-west-2.compute.internal \
  --ignore-daemonsets --delete-emptydir-data

# Check Karpenter's provisioning decisions.
kubectl logs -n karpenter deploy/karpenter -c controller --tail=200
```

## Related docs

- ADR-0031: ECS → EKS migration
- `runbooks/eks-node-replacement.md`
- `runbooks/coredns-recovery.md`
- `postmortems/2025-06-12-eks-upgrade-outage.md`
