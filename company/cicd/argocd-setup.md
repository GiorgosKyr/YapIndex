---
title: ArgoCD Setup
category: cicd
author: Priya Ramanathan
team: Platform
created: 2024-05-20
updated: 2026-01-28
status: current
version: 2.5
---

# ArgoCD Setup

Meridian runs a single ArgoCD instance in the **`meridian-tools-usw2`**
cluster. It manages every deployable Kubernetes workload across the three
workload clusters (prod, staging, dev). All manifests live in a separate
repo, **`meridian/deploy`**, which is the only Git repo ArgoCD reads.

## Cluster & install

- Cluster: `meridian-tools-usw2` (small EKS cluster, 3× `m6i.large`).
- Namespace: `argocd`.
- Installation via the upstream Helm chart, pinned major version.
- Ingress: `argocd.mrdn.io` behind Okta OIDC (no local admin login;
  the `admin` account is disabled).
- Datadog integration: metrics from `argocd-metrics` and application
  sync results as Datadog events.

## App-of-apps

We use the classic **app-of-apps** pattern. There is a single root
`Application` per environment that points at
`meridian/deploy/apps/<env>/`, which contains one child `Application` or
`ApplicationSet` per service.

```
meridian/deploy/
├── apps/
│   ├── prod/
│   │   ├── root.yaml                # root Application
│   │   └── applicationsets/
│   │       └── services.yaml        # generates a child app per service
│   ├── staging/
│   └── dev/
├── base/
│   ├── aurora/
│   ├── beacon/
│   ├── ledger/
│   ├── gatekeeper/
│   ├── portal/
│   ├── pulse/
│   ├── relay/
│   └── … one dir per service …
└── overlays/
    ├── prod/
    │   ├── aurora/
    │   │   └── kustomization.yaml   # image tag lives here
    │   └── …
    ├── staging/
    └── dev/
```

### ApplicationSet per environment

One `ApplicationSet` per env drives the fan-out. The generator is a
**list** of services (yes, hard-coded — we tried the git-directory
generator and it produced too many surprises).

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: services-prod
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - {service: aurora,     wave: "20"}
          - {service: pulse,      wave: "20"}
          - {service: beacon,     wave: "30"}
          - {service: beacon-aggregator, wave: "30"}
          - {service: portal,     wave: "40"}
          - {service: ledger,     wave: "30"}
          - {service: gatekeeper, wave: "10"}
          - {service: relay,      wave: "40"}
          - {service: compass,    wave: "40"}
          - {service: cartograph, wave: "30"}
          - {service: lighthouse, wave: "40"}
  template:
    metadata:
      name: "{{service}}-prod"
      annotations:
        argocd.argoproj.io/sync-wave: "{{wave}}"
    spec:
      project: prod
      source:
        repoURL: git@github.com:meridian/deploy.git
        targetRevision: main
        path: overlays/prod/{{service}}
      destination:
        server: https://kubernetes.meridian-prod-usw2
        namespace: "{{service}}"
      syncPolicy:
        automated: null           # prod = manual sync
        syncOptions:
          - CreateNamespace=true
```

## Overlays (Kustomize per env)

Each service has a `base/<service>/` with the shared manifests
(Deployment/Rollout, Service, HPA, ConfigMap, ServiceMonitor) and one
overlay per environment (`overlays/prod/<service>/`, etc.). The overlay
sets image tag, replica counts, resource requests, and env-specific
config. Helm is used only for a handful of third-party charts (cert-manager,
external-dns, external-secrets); everything Meridian-owned is Kustomize.

## Sync waves for DB migrations

Services that run schema migrations use a wave-ordered `Job` that runs
**before** the Rollout. Convention:

- Wave `-10`: pre-sync migration `Job` (annotated
  `argocd.argoproj.io/hook: PreSync`).
- Wave `0`–`10`: the shared infrastructure (Gatekeeper first — everyone
  depends on auth).
- Wave `20`–`40`: application services in dependency order.

The migration `Job` uses `hook-delete-policy:
BeforeHookCreation,HookSucceeded` so a stuck migration doesn't block the
next sync.

## Sync policy: auto in staging, manual in prod

| Env      | `automated.selfHeal` | `automated.prune` | Notes                              |
|----------|----------------------|-------------------|------------------------------------|
| dev      | true                 | true              | every commit lands automatically   |
| staging  | true                 | true              | auto on merge to `main`            |
| prod     | (unset — manual)     | (unset)           | click Sync in ArgoCD after review  |

## Notifications

ArgoCD Notifications posts sync outcomes to **`#eng-deploys`** in Slack:

- ✅ Sync succeeded (info-color).
- 🟡 Sync degraded / OutOfSync > 30 min.
- ❌ Sync failed.

Rollout events from Argo Rollouts (canary aborted, promoted, etc.) also
post to `#eng-deploys`. SEV-1/SEV-2-worthy events additionally page via
PagerDuty (see `runbooks/deploy-failure-triage.md`).

## Related

- `cicd/deploy-pipeline.md`
- `cicd/release-process.md`
- `runbooks/deploy-failure-triage.md`
