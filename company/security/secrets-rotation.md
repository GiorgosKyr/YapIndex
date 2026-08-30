---
title: Secrets Rotation Policy
category: security
author: Dara Okonkwo
team: Security
created: 2024-11-20
updated: 2026-06-30
status: current
version: 2.6
---

# Secrets Rotation Policy

Meridian rotates production secrets on a **quarterly** cadence by
default, with a few exceptions noted below. This document is the
**policy** — the *procedure* for actually performing a rotation, and the
emergency-rotation flow triggered by suspected compromise, lives in
`runbooks/rotate-production-secrets.md`. If those two documents ever
disagree on the actual steps, the runbook is authoritative and this
policy should be brought in line at the next revision.

## What rotates on the quarterly cadence

- **Stripe API key** — production restricted key used by Ledger.
- **DB passwords** — Postgres application user passwords for every
  service that connects to `meridian_app`. (Note: Redis and MSK do **not**
  need this — they use IAM auth, no static credentials.)
- **External vendor tokens** — Postmark, Customer.io, LaunchDarkly,
  PagerDuty, WorkOS webhook secrets. WorkOS in particular has caught us
  out before: INC-2026-05-19 was a WorkOS webhook secret rotation that
  did not propagate to Gatekeeper.
- **Datadog API and application keys** (for the Datadog Terraform
  provider and for the CI integration).
- **Third-party OAuth client secrets** where we are the client.

## Exceptions

- **JWT signing keys** are rotated by **KMS auto-rotate on an annual
  schedule**, not quarterly — see `security/authentication.md`.
  Quarterly manual rotation isn't necessary because the key never
  leaves KMS and rotation is invisible to consumers thanks to JWKS.
- **MSK IAM auth** — no static credentials to rotate. IAM role trust
  policies are reviewed annually.
- **ElastiCache Redis auth** — IAM RBAC, no AUTH tokens to rotate.
- **Write keys (customer-facing)** are on a customer-driven cadence;
  they are not on Meridian's rotation calendar.

## Storage

All secrets live in AWS Secrets Manager (production account
`meridian-prod`). Services fetch on startup and refresh every 5 minutes.
No secrets in environment variables baked into container images. No
secrets in Git — pre-commit hooks and `trufflehog` in CI enforce this.

## Cadence and calendar

- Q1 rotation window: **first two weeks of February**.
- Q2 rotation window: **first two weeks of May**.
- Q3 rotation window: **first two weeks of August**.
- Q4 rotation window: **first two weeks of November**.

Windows are two weeks so the on-call rotation naturally covers the
work. A Jira epic (`SEC-ROT-YYYY-QN`) tracks each cycle and includes a
checklist of every secret. The epic must close before the window ends.

## Emergency rotation

If a secret is *suspected* to be compromised — leaked in a log, pushed
to a public repo, exposed in a bug bounty report, or handled by a
laptop reported lost — treat it as compromised and rotate immediately.
The procedure is the same as the quarterly one but with everything
happening on a shorter clock and with the Security on-call driving.

**The runbook (`runbooks/rotate-production-secrets.md`) is the
authoritative reference for emergency rotation steps.** This policy
document intentionally does not duplicate them, because the last thing
you want during an incident is two divergent step lists.

## Audit

Every rotation writes an audit record to the `meridian-security` account
log archive. Vanta consumes these records for SOC 2 evidence (see
`security/compliance-soc2.md`).

## Related

- `runbooks/rotate-production-secrets.md` (authoritative procedure)
- `security/authentication.md`
- `security/compliance-soc2.md`
