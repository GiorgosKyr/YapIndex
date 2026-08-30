---
title: Deploy Pipeline (CI → ECR → ArgoCD)
category: cicd
author: Ben Ortiz
team: SRE
created: 2024-05-14
updated: 2025-11-06
status: current
version: 4.0
---

# Deploy Pipeline

This is the **current** deploy pipeline for Meridian services. It replaced
the Jenkins + custom deploy-scripts flow in May 2024 (see
`runbooks/deployment-process.md` — the version in `runbooks/` marked
`deprecated` still describes Jenkins; the current runbook is under
`cicd/`).

## Pipeline shape

```
PR opened / updated
   │
   ▼
GitHub Actions
   ├── lint (ruff / golangci-lint / eslint)
   ├── unit tests (pytest / go test / vitest)
   ├── integration tests (pytest with docker-compose)
   ├── security scan (tfsec, trivy image scan)
   └── build container → push to ECR
           │
           ▼
      (on merge to main)
           │
           ▼
    Update image tag in deploy repo
           │
           ▼
        ArgoCD
    ├── detects Git manifest change
    ├── syncs to EKS
    └── Argo Rollouts drives canary
```

## Stage 1: CI on the PR

Every service repo (`meridian/aurora`, `meridian/beacon`, `meridian/ledger`,
etc.) uses the reusable workflows from `meridian/gh-actions` (see
`cicd/github-actions-conventions.md`).

- **lint** — language-appropriate linter, must pass.
- **unit tests** — required, must pass.
- **integration tests** — spin up Postgres, Redis, sometimes Kafka via
  `docker compose`, run the service's integration suite.
- **security** — `trivy image` on the built container; MEDIUM+ vulns fail
  the build unless waived in `.trivyignore`.
- **build** — container image tagged
  `<service>:<git-sha>` and pushed to ECR
  (`730914662108.dkr.ecr.us-west-2.amazonaws.com/<service>`).

Credentials to ECR are obtained through **OIDC federation** — no long-lived
AWS keys sit in GitHub secrets (see the OIDC note in
`cicd/github-actions-conventions.md`).

## Stage 2: Bump the manifest

On merge to `main`, the same reusable workflow opens a PR against
`meridian/deploy` that updates the Kustomize overlay's `newTag:` for the
matching service:

```yaml
# meridian/deploy/overlays/staging/beacon/kustomization.yaml
images:
  - name: beacon
    newName: 730914662108.dkr.ecr.us-west-2.amazonaws.com/beacon
    newTag: f4c2e3a           # <— set by CI
```

**Staging** deploy-repo PRs are auto-merged (once required checks pass).
**Production** deploy-repo PRs wait for a human approval before merge.

## Stage 3: ArgoCD sync

ArgoCD (in the `meridian-tools-usw2` cluster) polls the deploy repo every
3 minutes.

- **Staging** apps are `auto-sync=true, prune=true, selfHeal=true`.
- **Prod** apps are `auto-sync=false`. An SRE or the on-call for that
  service clicks Sync in the ArgoCD UI (or `argocd app sync <name>`).

See `cicd/argocd-setup.md` for the app-of-apps structure.

## Stage 4: Progressive delivery (Argo Rollouts)

Services that opted in (Portal, Beacon, Ledger, Gatekeeper, Aurora, Relay)
use **Argo Rollouts** with a canary strategy:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: beacon
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 25
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
      analysis:
        templates:
          - templateName: beacon-error-rate
        startingStep: 1
```

Weights: **10% → 25% → 50% → 100%**, five-minute bake between steps.
An `AnalysisTemplate` queries the Datadog error-rate SLI; if the canary's
5-min error rate exceeds prod baseline by 2× for two consecutive checks,
the rollout is aborted and the previous ReplicaSet is scaled back up.

Not every service uses canaries. Ingest-side services (Pulse, Cartograph)
use rolling updates because their traffic is queue-fed and a canary weight
concept doesn't naturally apply.

## Rollback

Preferred: **revert the git commit** on `meridian/deploy` that bumped the
image tag. ArgoCD reconciles within 3 minutes.

For emergencies where 3 minutes is too long, `argocd app rollback <name>
<revision>` will pin ArgoCD to a prior sync history entry. Only SRE or
Platform leads have the ArgoCD role for `rollback`.

Argo Rollouts also supports `kubectl argo rollouts undo <name>` which
promotes the previous ReplicaSet immediately. That is the right move if a
canary is mid-flight and misbehaving — the alternative (waiting for the
analysis run to abort on its own) can be a couple of minutes.

## Related

- `cicd/argocd-setup.md`
- `cicd/github-actions-conventions.md`
- `cicd/release-process.md`
- `runbooks/deployment-process.md` (current)
- `runbooks/deployment-process.md` (Jenkins, **deprecated** — do not use)
