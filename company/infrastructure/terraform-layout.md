---
title: Terraform Monorepo Layout
category: infrastructure
author: Priya Ramanathan
team: Platform
created: 2024-02-28
updated: 2026-05-10
status: current
version: 1.6
---

# Terraform Monorepo Layout

All infrastructure lives in one repo: **`meridian/infra`**. It is intentionally
a monorepo — we tried per-service repos in 2023 and ended up with drift
between the network module and the app modules within a week.

## Repository shape

```
meridian/infra/
├── README.md
├── .atlantis.yaml
├── stacks/
│   ├── prod-usw2/
│   │   ├── main.tf
│   │   ├── network.tf
│   │   ├── eks.tf
│   │   ├── data.tf              # RDS, MSK, ElastiCache
│   │   ├── dns.tf
│   │   ├── iam.tf
│   │   ├── terraform.tf         # backend + required_providers
│   │   └── variables.tf
│   ├── staging-usw2/
│   │   └── (same shape)
│   ├── dev-usw2/
│   ├── sandbox-usw2/
│   ├── security-usw2/
│   ├── shared-usw2/
│   └── org-mgmt/                # Organizations, SCPs (payer account)
├── modules/
│   ├── vpc/
│   ├── eks-cluster/
│   ├── eks-node-group/
│   ├── karpenter/
│   ├── rds-aurora-postgres/
│   ├── msk-cluster/
│   ├── elasticache-redis/
│   ├── s3-bucket/
│   ├── route53-zone/
│   ├── ecr-repo/
│   └── iam-role-oidc-github/
└── scripts/
    ├── tfsec.sh
    └── bootstrap-state.sh
```

Rules of thumb:

- **Stacks** own state. One state file per stack.
- **Modules** are stateless building blocks. No `terraform_remote_state`
  references inside modules — pass values via variables.
- Modules are versioned by git tag when a breaking change is unavoidable
  (e.g. `modules/rds-aurora-postgres@v3`), otherwise consumed from `main`.

## Remote state

State is stored in the **`meridian-shared`** account so that no single
workload account can nuke another's state.

- Backend: S3 bucket **`meridian-tf-state-prod`** (versioning + SSE-KMS,
  bucket policy denies non-TLS).
- Locking: DynamoDB table **`meridian-tf-locks`** (PAY_PER_REQUEST, LockID
  as hash key).
- Per-stack key: `stacks/<stack-name>/terraform.tfstate`.

Backend block used in every stack:

```hcl
terraform {
  required_version = ">= 1.7.0"

  backend "s3" {
    bucket         = "meridian-tf-state-prod"
    key            = "stacks/prod-usw2/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "meridian-tf-locks"
    encrypt        = true
    kms_key_id     = "alias/meridian-tf-state"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}
```

## Apply flow (Atlantis)

We use **Atlantis** as the apply gate. It runs in the `meridian-shared`
account on a small EKS deployment and assumes into each workload account
via an OIDC-fronted role.

The pull request flow:

1. Engineer opens a PR against `main` touching a stack directory.
2. Atlantis auto-runs `terraform plan` for each affected stack and posts
   the diff as a PR comment.
3. Reviewer looks at the plan and the code diff.
4. Engineer comments `atlantis apply -d stacks/prod-usw2` after approval.
5. Atlantis applies. Merge is only allowed once the apply succeeds.

`.atlantis.yaml` autoplan example:

```yaml
version: 3
projects:
  - name: prod-usw2
    dir: stacks/prod-usw2
    workspace: default
    terraform_version: v1.7.5
    autoplan:
      when_modified:
        - "*.tf"
        - "../../modules/**/*.tf"
      enabled: true
    apply_requirements: [approved, mergeable]
```

Prod applies require two approvals from Platform (or one Platform + one SRE).
Staging is a single approval.

## Conventions

- Every resource carries `tags = local.common_tags`. `common_tags` includes
  `service`, `team`, `env`, `managed-by = "terraform"`.
- No `count` for optional resources — use `for_each` on a map so identity
  is stable across refactors.
- No inline `aws_iam_policy_document` blocks longer than 30 lines — extract
  to `iam/*.json` and load with `file()`.
- `tfsec` runs in CI (see `cicd/github-actions-conventions.md`). Findings
  above MEDIUM fail the build.

## Related

- `infrastructure/aws-accounts.md`
- `infrastructure/vpc-and-networking.md`
- ADR-0028: Terraform monorepo
