---
title: AWS Accounts & Access
category: infrastructure
author: Priya Ramanathan
team: Platform
created: 2024-02-11
updated: 2026-07-14
status: current
version: 2.3
---

# AWS Accounts & Access

This document describes how Meridian Data organizes AWS accounts under AWS
Organizations, and how engineers get access via Okta → AWS IAM Identity Center
(formerly AWS SSO).

## Organization layout

The management (payer) account holds only Organizations, Control Tower, and
consolidated billing. No workloads run there.

| Account            | Account ID     | Purpose                                             | OU               |
|--------------------|----------------|-----------------------------------------------------|------------------|
| `meridian-mgmt`    | `418239004521` | Payer / Organizations / SCPs                        | Root             |
| `meridian-prod`    | `730914662108` | Production workloads (Aurora, Pulse, Beacon, etc.)  | Workloads/Prod   |
| `meridian-staging` | `812477390644` | Full staging mirror                                 | Workloads/Nonprod|
| `meridian-dev`     | `605128337209` | Shared dev cluster, engineer branches               | Workloads/Nonprod|
| `meridian-sandbox` | `947103628815` | Demo/sales; reset weekly by scheduled Lambda        | Workloads/Nonprod|
| `meridian-security`| `264518903772` | GuardDuty admin, log archive, Security Hub          | Security         |
| `meridian-shared`  | `582049136774` | Shared services: Atlantis, ECR mirrors, ArgoCD tools| Shared           |

Service Control Policies (SCPs) applied at the Workloads OU:

- Deny `s3:PutBucketPolicy` that would make a bucket public unless tagged
  `public-ok=true`.
- Deny non-approved regions (only `us-west-2`, `us-east-1`, and — starting
  Q4 2026 — `eu-central-1`).
- Deny root user access except from the break-glass session.

## SSO / access

- Identity provider: **Okta**. Users are provisioned into an Okta group
  (`aws-<account>-<role>`, e.g. `aws-prod-developer`).
- Okta federates into **AWS IAM Identity Center** (the artist-formerly-known-as
  AWS SSO), which owns the permission sets.
- Engineers log in via `https://meridian.awsapps.com/start` and pick an
  account/role tile.

### Permission sets

The same four permission sets are provisioned in every workload account:

| Permission set | Managed policies                                       | Session (h) | Who              |
|----------------|--------------------------------------------------------|-------------|------------------|
| `Developer`    | ReadOnlyAccess + a scoped inline policy (see below)    | 8           | All engineers    |
| `Deployer`     | Developer + CI-scoped write (ECR push, ECS/EKS deploy) | 4           | CI OIDC roles    |
| `Admin`        | AdministratorAccess                                    | 1           | Platform + SRE   |
| `ReadOnly`     | ReadOnlyAccess                                         | 12          | Product/Finance  |

`Developer` allows console poking and log reading, plus write access to a
handful of scratch S3 buckets (`s3://meridian-dev-scratch-*`). It does NOT
allow IAM writes, EKS API access, or KMS decrypt for anything under
`alias/gatekeeper-*`.

`Admin` in `meridian-prod` is limited to Platform + SRE leads (Priya, Ben,
Marcus). Every session is logged to the security account via CloudTrail
organization trail.

## Break-glass

If IAM Identity Center is unavailable (Okta outage, region issue), each
account still has a root user with MFA hardware key. Root credentials are
stored in 1Password vault **`ops-critical`** (access: CTO, VP Eng, Head of
Platform, Head of Security). The MFA YubiKey lives in the Seattle office
safe with a duplicate at Priya's home office.

Using break-glass triggers:

1. A PagerDuty page to the on-call Platform lead (via CloudTrail EventBridge
   rule matching `userIdentity.type = "Root"`).
2. A required incident write-up in `incidents/` within 48h.

## Common tasks

Assume the `Developer` role from CLI (uses `aws sso login`):

```bash
aws sso login --profile prod-dev
aws --profile prod-dev sts get-caller-identity
```

`~/.aws/config` snippet:

```ini
[profile prod-dev]
sso_start_url = https://meridian.awsapps.com/start
sso_region    = us-west-2
sso_account_id = 730914662108
sso_role_name = Developer
region        = us-west-2
```

See also: `infrastructure/vpc-and-networking.md`,
`infrastructure/secrets-management.md`,
`runbooks/rotate-production-secrets.md`.
