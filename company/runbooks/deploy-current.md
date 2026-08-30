---
title: Deploying Services to Production (Current)
category: runbook
author: Priya Ramanathan
team: Platform
created: 2024-05-30
updated: 2025-11-04
status: current
version: 2.0
---

# Deploying Services to Production

This is the **current** deployment procedure for all Meridian services running
on EKS. It replaced the Jenkins-based flow in 2024-Q2 (see
`runbooks/deploy-legacy-jenkins.md`, marked deprecated).

## Preconditions

- Your PR has been merged to `main`.
- All required CI checks are green: `build`, `unit`, `integration`, `sast`,
  `container-scan`.
- You have `argocd` CLI ≥ 2.9 and are logged in
  (`argocd login argocd.mrdn.io --sso`).
- You have access to the SRE bastion (`bastion-01.prod.mrdn.io`) via SSO —
  `argocd app sync ... -prod` is only allowed from a bastion source IP.
- The service you are deploying is not currently frozen (check `#eng-oncall`
  for freeze banners; freezes are declared around SEV-1s and end-of-quarter).

## Steps

### Normal path (auto-staged, manual prod promote)

1. Merge to `main`. GitHub Actions runs `.github/workflows/release.yml`:
   - Builds the container.
   - Pushes to ECR `123456789012.dkr.ecr.us-west-2.amazonaws.com/<service>:<sha>`.
   - Updates the Kustomize overlay in the
     `meridian-manifests` repo (`overlays/staging/<service>/kustomization.yaml`)
     via a bot commit.
2. ArgoCD detects the manifest change and auto-syncs to `staging`. Watch:
   ```bash
   argocd app get <service>-staging
   ```
3. Bake time in staging: **30 min minimum** for user-facing services
   (Portal, Beacon, Ledger, Gatekeeper). 10 min for internal (Atlas,
   Cartograph, Lighthouse). Check the `staging health` Datadog dashboard.
4. Open a promotion PR in `meridian-manifests` that bumps
   `overlays/prod/<service>/kustomization.yaml` to the same image tag.
   Requires 1 approval from the service's owning team (see canon §3).
5. Merge the promotion PR. From the bastion:
   ```bash
   ssh bastion-01.prod.mrdn.io
   argocd app sync <service>-prod
   argocd app wait <service>-prod --health --timeout 600
   ```
   Expected: `Synced` and `Healthy` within 5-10 min for most services.

### Hotfix path

For SEV-1/SEV-2 fixes, an approver in `#eng-oncall` can grant a
`hotfix` label on the promotion PR, which bypasses the 30-min staging bake
(but *not* the CI checks).

## Verification

- `argocd app get <service>-prod` shows `Sync Status: Synced` and
  `Health Status: Healthy`.
- Datadog service dashboard for `<service>` — error rate < 0.5% for 10 min
  post-deploy.
- Sentry: no new issue with `first_seen` after your deploy timestamp above
  10 events / minute.
- If the service exposes `/version`, curl it and confirm the returned SHA
  matches your commit.

## Rollback

Rollback is **manifest-driven**, not image-driven, so it's always a git
revert:

1. In `meridian-manifests`, revert the promotion commit:
   ```bash
   git revert <sha-of-promotion>
   git push origin main
   ```
2. Merge the revert PR (label `rollback` waives approval).
3. ArgoCD auto-syncs prod back to the previous image tag within 60s.
4. Announce in `#eng-oncall`: "Rolled back `<service>` prod to `<old-sha>`".

Never use `kubectl rollout undo` in prod — ArgoCD will re-apply the bad
manifest within seconds and undo your undo.

## Contacts

- Platform on-call: `@platform-oncall` in `#eng-oncall`
- ArgoCD owner: Priya Ramanathan
- Bastion access issues: Dara Okonkwo (Security)
