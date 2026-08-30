---
title: Deploying Services to Production (Jenkins) — DEPRECATED
category: runbook
author: Ravi Patel
team: Platform
created: 2022-04-12
updated: 2024-06-03
status: deprecated
version: 1.9
---

> # WARNING — DO NOT FOLLOW THIS RUNBOOK
>
> This runbook is retained for **historical reference only**. The Jenkins
> deploy infrastructure it describes was **decommissioned in May 2024** as
> part of the ECS → EKS migration (see ADR-0031) and the move to GitHub
> Actions + ArgoCD.
>
> - Jenkins host `ci.mrdn.io` no longer exists (DNS record removed 2024-06-14).
> - The `deploy-prod.sh` script has been removed from the `meridian-ops` repo.
> - The ECS clusters `meridian-prod-ecs` and `meridian-staging-ecs` were
>   torn down 2024-05-22.
>
> **The current deploy runbook is `runbooks/deploy-current.md`.**
>
> If you found this doc via search and thought it looked authoritative:
> please update your bookmarks and let `#eng-platform` know how you got here
> so we can improve routing.

---

# Deploying Services to Production (Legacy Jenkins Flow)

*Originally written 2022-04, last substantive edit 2024-01, deprecation
banner added 2024-06.*

At the time of writing, Meridian's ~9 services ran on ECS Fargate in
`meridian-prod-ecs`. Deploys were orchestrated by Jenkins, with a shell
script (`ops/deploy-prod.sh`) that wrapped `aws ecs update-service` and
posted to Slack.

## Preconditions (historical)

- SSH key on file in the `meridian-ops` deploy-keys bag.
- Jenkins account with the `prod-deploy` role.
- You are on the bastion `bastion.mrdn.io` (the old bastion, not the
  current `bastion-01.prod.mrdn.io`).
- The service you're deploying passed the `meridian-ci/<service>` Jenkins
  pipeline. Green build number recorded (e.g. `#4821`).

## Steps (historical — DO NOT RUN)

1. SSH to the bastion:
   ```bash
   ssh <user>@bastion.mrdn.io
   ```
2. Assume the deploy role:
   ```bash
   eval "$(aws-vault exec meridian-prod-deploy -- env | grep AWS_)"
   ```
3. Open Jenkins in a browser: `https://ci.mrdn.io/job/meridian-deploy/`.
4. Click **Build with Parameters**. Fill in:
   - `SERVICE`: one of `aurora`, `beacon`, `ledger`, `gatekeeper`,
     `compass`, `atlas`, `cartograph`, `portal`, `relay`.
     (`pulse` was added to this list in 2023-03; before that Aurora wrote
     to ClickHouse directly.)
   - `SHA`: the merge commit SHA on `main`.
   - `TARGET`: `prod`. (`staging` deploys were automatic on push.)
5. Click **Build**.
6. Jenkins ran, on the executor node, roughly:
   ```
   ops/deploy-prod.sh <service> <sha>
   ```
   which built the image, pushed to ECR, updated the ECS task definition,
   and called `aws ecs update-service --force-new-deployment`.
7. Wait for the Slack notification in `#deploys`:
   > `[prod] beacon @a1b2c3d4 — DEPLOYED (4m 12s)`
8. On failure, Slack would post `— FAILED` and link to the Jenkins console.
   Recovery was to click **Rebuild** with the previous known-good SHA, or
   run `ops/rollback-prod.sh <service>` from the bastion.

## Verification (historical)

- CloudWatch dashboard `meridian-prod / ecs-services` — task count matched
  desired count.
- New Relic APM (retired 2024-Q3) — error rate for `<service>` under
  baseline for 10 min.
- Curl `https://api.meridiandata.io/<service>/version` and confirm SHA.

## Rollback (historical)

```bash
ssh bastion.mrdn.io
ops/rollback-prod.sh <service>
```

which repointed the ECS service to the previous task definition revision.

## Why this was replaced

By late 2023, the Jenkins deploy pipeline had accumulated significant
operational debt:

- ECS task-definition sprawl made per-service config drift the norm.
- Jenkins host was a snowflake — no IaC, plugins upgraded by hand.
- No declarative reconciliation: manual `kubectl`/`ecs` edits during
  incidents were never reverted, so state diverged from `main`.
- `deploy-prod.sh` had grown to 1,200 lines of bash.

ADR-0031 (ECS → EKS) and the follow-up decision to adopt ArgoCD retired
this pipeline. The final Jenkins deploy was on **2024-05-19**
(`gatekeeper @f0e1d2c3`). Jenkins was shut down 2024-05-22.

## Contacts (historical, likely stale)

- Original owner: Ravi Patel (then acting head of platform).
- 2023 owner: the Platform team, before Priya joined.

For anything current, see `runbooks/deploy-current.md` and `#eng-platform`.
