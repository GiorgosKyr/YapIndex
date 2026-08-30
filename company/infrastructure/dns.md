---
title: DNS & Route53
category: infrastructure
author: Ben Ortiz
team: SRE
created: 2024-05-01
updated: 2026-03-19
status: current
version: 1.4
---

# DNS & Route53

Meridian owns three Route53 hosted zones (plus a legacy one that only 301s).
DNS records for services are managed by the **External DNS** controller
running in each EKS cluster; TLS certificates are issued and auto-renewed
through ACM.

## Hosted zones

| Zone                  | Type    | Account            | Purpose                                        |
|-----------------------|---------|--------------------|------------------------------------------------|
| `meridiandata.io`     | public  | `meridian-shared`  | Customer-facing hostnames                      |
| `mrdn.io`             | public  | `meridian-shared`  | Short internal links, share URLs, short-links  |
| `meridian.internal`   | private | `meridian-shared`  | Internal service discovery (associated to all VPCs) |
| `getmeridian.com`     | public  | `meridian-shared`  | Legacy; 301 to `meridiandata.io`               |

The private zone is associated with every workload VPC via the Transit
Gateway account. Split-horizon is intentional — internal services never
resolve from outside the corporate VPN.

## Ingress hostnames

The three main customer-facing hostnames:

| Hostname                     | Backend                                | Notes                                    |
|------------------------------|----------------------------------------|------------------------------------------|
| `api.meridiandata.io`        | **Aurora** (ingest) via public ALB     | Rate limits at ALB + Aurora both         |
| `app.meridiandata.io`        | **Portal** via public ALB              | Next.js SSR, served from EKS             |
| `beacon.meridiandata.io`     | **Beacon** via internal ALB            | **Internal-only** — VPN or office IP     |

Yes, the fact that `beacon.meridiandata.io` is internal-only trips people
up — it is reached from Portal server-side, not from the browser. The
public-facing query API from customer scripts terminates at
`api.meridiandata.io/v3/query`, which the ALB routes to Beacon after JWT
verification by Gatekeeper.

Other notable hostnames:

- `docs.meridiandata.io` — static docs site (Cloudflare Pages, not our EKS).
- `status.meridiandata.io` — Statuspage.io.
- `auth.meridiandata.io` — Gatekeeper OIDC/OAuth endpoints (public ALB).
- `webhooks.meridiandata.io` — Relay's callback receiver (public ALB).
- `stripe-webhook.meridiandata.io` → Ledger.

Internal:

- `argocd.mrdn.io` — ArgoCD UI (behind Okta OIDC).
- `atlantis.mrdn.io` — Atlantis.
- `grafana.mrdn.io` — Grafana (metrics from Datadog federation, some
  self-hosted dashboards).

## External DNS

Each EKS cluster runs the **External DNS** controller. It watches
`Ingress` and `Service` objects annotated with
`external-dns.alpha.kubernetes.io/hostname` and reconciles the matching
record in Route53. It has IRSA-based access scoped to the two public zones.

Example annotation on a Portal ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: portal
  namespace: product
  annotations:
    external-dns.alpha.kubernetes.io/hostname: app.meridiandata.io
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:730914662108:certificate/…
```

External DNS runs with `--policy=upsert-only` in prod. It will never
delete a record. Removing DNS records is a manual, PR-reviewed change in
`stacks/prod-usw2/dns.tf`.

## ACM certificates

- All public certs are ACM in the same region as the load balancer.
- Wildcard cert `*.meridiandata.io` covers most hostnames; per-service
  certs are only issued when we need a hostname outside the wildcard
  (e.g. two-label deeper names).
- DNS validation records live in the same Route53 zone → auto-renewal is
  hands-off.
- CloudFront distributions requiring `us-east-1` certs (docs, marketing)
  use a separate wildcard issued there.

## Private zone conventions

Internal service records live in `meridian.internal`. Convention:
`<service>.<env>.meridian.internal`, e.g.:

- `beacon.prod.meridian.internal`
- `aurora.prod.meridian.internal`
- `postgres.prod.meridian.internal` — CNAME to the Aurora RDS writer.

Within a Kubernetes namespace, services still use k8s DNS
(`beacon.product.svc.cluster.local`); the `meridian.internal` names are
for anything that lives outside the cluster (e.g. a bastion, a script on
a scheduled Lambda).

## Legacy: `getmeridian.com`

The 2019–2021 marketing site was hosted on `getmeridian.com`. The zone is
kept — a small CloudFront distribution returns 301s to the equivalent
`meridiandata.io` path. Don't delete it; there are old blog inbound links
still resolving there.

## Related

- `infrastructure/vpc-and-networking.md`
- `infrastructure/eks-cluster.md`
