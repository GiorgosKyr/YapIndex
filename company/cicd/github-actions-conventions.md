---
title: GitHub Actions Conventions
category: cicd
author: Ben Ortiz
team: SRE
created: 2024-06-02
updated: 2026-02-17
status: current
version: 2.2
---

# GitHub Actions Conventions

Every Meridian service repo uses GitHub Actions, and every service repo
consumes a **reusable workflow** from **`meridian/gh-actions`** rather
than owning its own CI logic. That way, when we change the way we scan
images or bump a language toolchain, we do it in one place.

## Workflow file layout

Every service repo has these three files, exactly:

```
.github/
  workflows/
    ci.yml          # runs on PR and push to main
    cd.yml          # runs on push to main; bumps deploy repo
    security.yml    # nightly scans + Dependabot review
```

Additional workflows (release, docs, whatever) live outside these three
paths and don't gate merges.

### `ci.yml` template

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    uses: meridian/gh-actions/.github/workflows/service-ci.yml@v3
    with:
      language: python
      python_version: "3.11"
      integration_tests: true
    secrets: inherit
```

The reusable workflow expands into `lint`, `unit`, `integration`, `build`,
and `scan` jobs. Job matrices are pinned inside the reusable workflow so
consumer repos don't drift.

### Standard matrix

| Language   | Version pinned in reusable WF | Notes                     |
|------------|-------------------------------|---------------------------|
| Python     | 3.11                          | matches `pyproject`       |
| Go         | 1.22                          | matches `go.mod`          |
| Node       | 20                            | pnpm-based                |
| Rust       | 1.79                          | one repo (`shortener`)    |

Bumping any of these is a PR in `meridian/gh-actions` and a coordinated
rollout — do not upgrade in a single service repo by editing `ci.yml`
locally.

## OIDC to AWS

We stopped using long-lived AWS access keys in GitHub secrets in **November
2024**. Every workflow that needs AWS credentials now uses GitHub's OIDC
token exchange with an IAM role fronted by the
`aws-actions/configure-aws-credentials` action.

Each reusable workflow declares the role it needs:

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::730914662108:role/gh-actions-ecr-push
      aws-region: us-west-2
```

Roles live in `meridian/infra` under `modules/iam-role-oidc-github/` and
are scoped tightly:

- `gh-actions-ecr-push` — push to that service's ECR repo only.
- `gh-actions-deploy-bumper` — commit to `meridian/deploy` only (no AWS).
- `gh-actions-integration-test` — read-only access to a scratch S3 bucket
  and a Secrets Manager secret prefix `dev/ci/*`.

Trust policies pin `sub` on repo + branch + workflow file so a rogue
workflow in a fork cannot assume the role.

## Concurrency

Every workflow sets a `concurrency` block. The convention:

- **PR CI**: `ci-${{ github.workflow }}-${{ github.ref }}`, cancel in
  progress. A new push cancels the earlier run.
- **`main` CD**: `cd-${{ github.workflow }}-main`, **do not** cancel in
  progress — serialising deploy-bump PRs prevents race conditions on the
  `newTag:` field.

## Required checks

The following checks are required to merge into `main` on every service
repo (enforced by branch protection):

- `ci / lint`
- `ci / unit`
- `ci / integration`
- `ci / build`
- `ci / scan`

Waiving one requires a Platform lead to temporarily flip branch protection
in the repo settings, and the reason is logged in `#eng-oncall`.

## Secrets in Actions

Non-AWS secrets (GitHub tokens, Codecov, Datadog CI Visibility API key,
etc.) live in **org-level** GitHub Secrets and are inherited via
`secrets: inherit`. Repo-level secrets are strongly discouraged — they
drift across repos and are hard to audit.

## What lives in `meridian/gh-actions`

- `.github/workflows/service-ci.yml` — the canonical service CI.
- `.github/workflows/service-cd.yml` — bumps the tag in `meridian/deploy`.
- `.github/workflows/security-nightly.yml` — nightly `trivy fs` + `trivy
  image` scans, results uploaded to GitHub Code Scanning.
- Composite actions in `actions/` for common steps (Setup, Login, Tag).

Updates to `meridian/gh-actions` are cut with git tags (`v3`, `v3.1`, …).
Consumer repos pin to a major (`@v3`) and get patch updates for free.

## Related

- `cicd/deploy-pipeline.md`
- `cicd/argocd-setup.md`
- `infrastructure/terraform-layout.md` (`modules/iam-role-oidc-github/`)
