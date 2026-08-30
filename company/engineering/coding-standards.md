---
title: Coding Standards
category: engineering
author: Priya Ramanathan
team: Platform
created: 2023-06-10
updated: 2026-07-14
status: current
version: 3.0
---

# Coding Standards

Applies to all first-party code at Meridian Data. New services MUST comply
on day one; existing services are being brought up to spec incrementally.
Deviations require a note in the PR description and reviewer sign-off.

See also: `code-review-guidelines.md`, `language-choices.md`,
`tech-radar.md`.

## Python (3.11)

Python is the default for business-logic and iteration-heavy services:
Beacon, Ledger, Compass, Atlas, Lighthouse, Beacon-Aggregator.

- **Formatter:** `black`, line length 100. No config drift — every repo
  uses the shared `pyproject.toml` fragment from `platform/python-baseline`.
- **Linter:** `ruff` with the ruleset in `platform/python-baseline`
  (`E, F, I, N, UP, S, B, A, C4, PT, SIM, TID`). `ruff --fix` is expected
  to pass in CI.
- **Types:** `mypy --strict` is required for **new code and new modules**.
  Legacy modules are exempted via `mypy.ini` `[mypy-<pkg>.*]` blocks; the
  exemption list only shrinks. No new `# type: ignore` without a reason
  comment.
- **Dependency management:** `uv` (adopted 2026-Q1, replaced Poetry).
  Lockfiles committed. No unpinned deps in `pyproject.toml`.
- **Async:** prefer `async def` in FastAPI handlers. Blocking calls
  (Stripe SDK, some Postgres drivers) go through `asyncio.to_thread` or
  a dedicated worker.
- **Logging:** `structlog` with the shared processor chain. Never log full
  JWTs, API keys, or PII. See INC-2024-08-05.

### Python testing

- `pytest` with `pytest-asyncio` (mode = auto).
- Unit tests live next to the module in `tests/`. Integration tests under
  `tests/integration/` and gated behind `pytest -m integration`.
- Coverage floor: **80%** for services in Beacon/Ledger/Compass; **70%**
  elsewhere. Enforced by `pytest --cov --cov-fail-under`.
- Fixtures for Postgres via `testcontainers`. ClickHouse uses a shared
  ephemeral instance per CI job.

## Go (1.22)

Go is the default for perf-critical and high-throughput services: Aurora,
Pulse, Gatekeeper, Relay, Cartograph.

- **Formatter:** `gofmt` + `goimports`. CI fails on unformatted diffs.
- **Linter:** `golangci-lint run` with `.golangci.yml` from
  `platform/go-baseline`. Enabled linters include `govet`, `staticcheck`,
  `errcheck`, `gosec`, `revive`, `gocritic`, `bodyclose`.
- **Modules:** Go modules, minimum version pinned in `go.mod`.
  `go mod tidy` must be clean on every PR.
- **Errors:** wrap with `fmt.Errorf("...: %w", err)`. No `panic()` in
  request paths. Sentinel errors in a package-level `errors.go`.
- **Context:** every exported function that does IO takes
  `context.Context` as its first argument.
- **HTTP:** `chi` router. `zap` for logging (sugared logger discouraged
  for hot paths).

### Go testing

- `go test ./... -race` in CI.
- Table-driven tests preferred. `testify/require` is allowed; `assert` is
  discouraged (silent continues mask bugs).
- Benchmarks required for anything on the ingest hot path (Aurora
  handlers, Pulse enrichment steps). Regressions >5% block merge.

## TypeScript

TS is used for Portal (Next.js 14) and for the shared packages
`@meridian/ui` and `@meridian/sdk`. See `architecture/portal-architecture.md`.

- **Node:** 20 LTS.
- **Package manager:** `pnpm`. Workspaces are defined at the monorepo root.
- **Formatter:** `prettier` (config in `.prettierrc` at repo root, do not
  override per-package).
- **Linter:** `eslint` with `@meridian/eslint-config` (extends
  `next/core-web-vitals`, `plugin:@typescript-eslint/recommended-type-checked`).
- **Types:** `tsconfig.json` sets `strict: true`, `noUncheckedIndexedAccess: true`,
  `noImplicitOverride: true`. No `any` in new code; use `unknown` and narrow.
- **React:** functional components only. Server Components by default in
  App Router pages; opt into `"use client"` explicitly.

### TS testing

- `vitest` for unit tests, `playwright` for e2e. Playwright suites run
  nightly against staging.
- Snapshot tests are discouraged for anything but stable design-system
  primitives.

## Cross-cutting

- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `chore:`,
  `refactor:`, `docs:`). Not enforced by hook, but PR templates prompt for it.
- **Secrets:** never in source, never in logs. Use Vault + the
  `platform/secrets` client library. See `runbooks/rotate-production-secrets.md`.
- **Feature flags:** LaunchDarkly for anything user-visible or risky.
  Flags older than 90 days are flagged for cleanup by the weekly cron.
