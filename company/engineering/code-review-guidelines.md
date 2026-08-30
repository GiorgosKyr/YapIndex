---
title: Code Review Guidelines
category: engineering
author: Marcus Oduya
team: Engineering
created: 2024-02-11
updated: 2026-05-30
status: current
version: 2.1
---

# Code Review Guidelines

How we review code at Meridian. The goals, in order: correctness,
maintainability, and shipping velocity. Reviews are a two-way conversation,
not a gate.

Related: `coding-standards.md`, `service-ownership.md`.

## Who needs to approve

| Change type | Required approvals |
|-------------|--------------------|
| Production service code (any service in `service-ownership.md`) | **2 approvals** |
| Shared libraries (`platform/*`, `@meridian/ui`, `@meridian/sdk`) | **2 approvals**, at least one from the owning team |
| Internal tooling, scripts, dev-only code | **1 approval** |
| Docs-only (`docs/`, `**/*.md`) | **1 approval** |
| Terraform in `prod/` | **2 approvals**, one from Platform |
| Terraform in `staging/`, `dev/` | **1 approval** |

Approvals must come from **users listed in `CODEOWNERS`** for the touched
paths. GitHub is configured with branch protection on `main` in every
service repo to enforce this; the check is called `codeowners-approved`.

Self-approvals do not count. Approving your own PR by pushing an empty
change on someone else's approval is a bypass — SRE runs a monthly audit
against the GitHub audit log.

## SLA

- **First review comment or approval within 4 business hours** of a PR
  being marked ready for review (out of draft).
- **Re-reviews within 2 business hours** of a push that addresses
  feedback.
- If you can't meet the SLA, reassign — don't leave the PR sitting.

Business hours are 09:00–18:00 in the reviewer's local timezone, Monday
to Friday. The `#code-review-help` Slack channel is the escape hatch when
your team's reviewers are all out.

## What we look for

In roughly this order:

1. **Does it work?** Does the change actually do what the PR description
   says it does? Are the tests testing the thing?
2. **Is it safe to deploy?** Migrations, feature flags, rollout plan.
   Anything touching Ledger billing paths gets extra scrutiny post
   INC-2025-03-08.
3. **Does it fit the codebase?** Consistent with `coding-standards.md`,
   uses existing helpers instead of reinventing.
4. **Is it observable?** Logs, metrics, traces. New endpoints need at
   minimum a request-count and latency histogram.
5. **Is it documented?** Runbook updates for anything that could page
   someone. ADR if it's an architectural choice.
6. **Style.** Last, and mostly automated — `ruff`, `golangci-lint`,
   `eslint` run in CI. Don't leave nit comments that the linter would catch.

## Small PRs are strongly preferred

- **Target:** <400 lines diff, excluding lockfiles and generated code.
- PRs >800 lines get an automatic Danger comment asking whether they can
  be split. They can still merge; it's a nudge, not a block.
- Big refactors: land a stacked series of small PRs (Graphite is
  supported but not mandatory). Merge behind a flag if user-visible.

Reviewers are allowed to request a split. "This is too big to review
carefully" is a legitimate blocking comment.

## Approval etiquette

- **Approve with comments** if the change is fine but you want cleanup:
  the author can address without a re-review.
- **Request changes** only for things that must be resolved before merge
  (bugs, security, wrong design). Not for style preferences.
- Prefix nits with `nit:` so the author can safely ignore.
- Reviewers can push trivial fixes directly to the branch (typo, missing
  import) — leave a comment saying you did.

## Merging

- **Squash-merge** is the default for all repos. The PR title becomes the
  commit subject; keep it Conventional-Commits-shaped.
- Merge is by the author, not the reviewer, unless the author explicitly
  asks otherwise.
- Do not merge with failing CI. "Flaky test" is not an override —
  re-run or fix.

## CODEOWNERS

Each service repo has a `CODEOWNERS` file at the root. Ownership is by
directory. The canonical service→team mapping lives in
`service-ownership.md`; `CODEOWNERS` must stay consistent with it. If
they disagree, `service-ownership.md` wins and the `CODEOWNERS` file
needs a PR.
