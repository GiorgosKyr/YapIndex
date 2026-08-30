---
title: VPC & Networking
category: infrastructure
author: Priya Ramanathan
team: Platform
created: 2024-03-02
updated: 2026-04-22
status: current
version: 2.4
---

# VPC & Networking

Every Meridian AWS account gets its own VPC in `us-west-2`. Accounts are
stitched together with a Transit Gateway; the security account is reached
through VPC peering (kept off the TGW to avoid transitive routing to log
storage).

## VPC CIDRs

| Account            | VPC CIDR         | Notes                                     |
|--------------------|------------------|-------------------------------------------|
| `meridian-prod`    | `10.20.0.0/16`   | Production workloads                      |
| `meridian-staging` | `10.30.0.0/16`   | Full mirror                               |
| `meridian-dev`     | `10.40.0.0/16`   | Shared dev                                |
| `meridian-sandbox` | `10.50.0.0/16`   | Reset weekly                              |
| `meridian-security`| `10.90.0.0/16`   | GuardDuty, log archive; peered, not TGW   |
| `meridian-shared`  | `10.80.0.0/16`   | Atlantis, ArgoCD, ECR mirrors             |

The Frankfurt buildout will use `10.60.0.0/16` (planned, not live).

IPv6 is **not** enabled. It has come up in Platform planning twice and been
deferred both times; there is no target date.

## Subnet layout (per VPC)

Each VPC has three tiers, one subnet per AZ (three AZs), for nine subnets
per VPC.

| Tier      | Purpose                                     | Prod CIDRs (example)                           |
|-----------|---------------------------------------------|------------------------------------------------|
| `public`  | ALBs, NAT gateways, bastion (if needed)     | `10.20.0.0/24`, `10.20.1.0/24`, `10.20.2.0/24` |
| `private` | EKS nodes, most workloads                   | `10.20.16.0/20`, `10.20.32.0/20`, `10.20.48.0/20` |
| `data`    | RDS, MSK, ElastiCache, OpenSearch           | `10.20.64.0/22`, `10.20.68.0/22`, `10.20.72.0/22` |

Private subnets are the big ones because Karpenter can churn hundreds of
nodes, and the VPC CNI hands each pod an ENI IP (with prefix delegation, a
/28 at a time).

## NAT gateways

Three NAT gateways per production VPC — one per AZ — for HA. Each private
subnet routes `0.0.0.0/0` to the NAT in its own AZ, so an AZ outage does not
force cross-AZ NAT charges. In staging and dev we run a **single** NAT to
save money; that's an accepted trade-off documented in ADR-0038.

## Inter-account connectivity

### Transit Gateway

- TGW name: `meridian-tgw-usw2`, owned by `meridian-shared`.
- Attachments: prod, staging, dev, sandbox, shared.
- Route tables:
  - `nonprod-rt` — staging/dev/sandbox can reach each other and shared.
  - `prod-rt` — prod can reach shared only.
  - Prod↔nonprod is denied at the TGW route-table level. This is the reason
    engineers cannot `curl` prod from a dev box.

### VPC peering to security

The security account VPC (`10.90.0.0/16`) is peered to every workload VPC.
Only egress to GuardDuty endpoints and the log-archive S3 gateway endpoint
is allowed via security group rules.

## Security groups

Security groups are grouped by service tier and referenced by ID from
Terraform module outputs. Cross-tier flow only opens on the ports the
downstream needs.

| SG                      | Ingress from                          | Egress                        |
|-------------------------|---------------------------------------|-------------------------------|
| `sg-eks-nodes-prod`     | ALBs (443), self (all), Datadog agent | 443 to anywhere               |
| `sg-rds-aurora-prod`    | `sg-eks-nodes-prod` on 5432           | none                          |
| `sg-msk-prod`           | `sg-eks-nodes-prod` on 9092/9094      | none                          |
| `sg-elasticache-prod`   | `sg-eks-nodes-prod` on 6379           | none                          |
| `sg-clickhouse-prod`    | `sg-eks-nodes-prod` on 8123/9000      | 443 to S3 gateway endpoint    |
| `sg-alb-public-prod`    | 0.0.0.0/0 on 443                      | `sg-eks-nodes-prod` on 30000-32767 |

Nothing except ALBs listens on `0.0.0.0/0`. Beacon's internal-only
hostname (`beacon.meridiandata.io`) is served by an internal-scheme ALB and
is only reachable through the corporate VPN (see
`infrastructure/dns.md`).

## VPC endpoints

To keep data traffic off NATs and off the public internet:

- Gateway endpoints: **S3**, **DynamoDB**.
- Interface endpoints: **ECR api + dkr**, **STS**, **Secrets Manager**,
  **KMS**, **Logs**, **SSM**.

Interface endpoints are shared across AZs; DNS override is on so any
`*.us-west-2.amazonaws.com` call resolves privately from within the VPC.

## Related

- `infrastructure/aws-accounts.md`
- `infrastructure/eks-cluster.md`
- ADR-0038: single-NAT in nonprod
