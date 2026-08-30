---
title: Portal Architecture
category: architecture
author: Elena Vasquez
team: Product Eng
created: 2024-05-22
updated: 2026-07-15
status: current
version: 4.0
---

# Portal Architecture

Portal is the customer-facing web app at `app.meridiandata.io`.
Next.js 14 on the App Router, TypeScript, deployed to EKS.

Related: `system-overview.md`, `service-map.md`,
`engineering/language-choices.md`, `engineering/coding-standards.md`.

## Runtime shape

- **Next.js 14 App Router.**
  - **SSR** for public marketing pages (`/`, `/pricing`, `/docs/*`,
    `/blog/*`). These need SEO and can render without a session.
  - **CSR** (client-rendered dashboard) for everything under
    `/app/*` — the authenticated dashboard. First paint is a small
    shell; the dashboard hydrates and fetches its data client-side
    against Beacon.
- Deployed as a standalone Next.js server behind an internal ALB
  (`alb-portal-prod`), CloudFront in front (`app.meridiandata.io`).
- Node 20 LTS in the container. Image built with the multi-stage
  Dockerfile from the monorepo root.

## Auth

- **Gatekeeper** issues JWTs (see `service-ownership.md` for owner).
- The JWT is stored in an **httpOnly, Secure, SameSite=Lax cookie**
  named `mrdn_sess`. It is never accessible to page JS — the SPA
  authenticates to Beacon via a tiny same-origin API route
  (`/api/proxy/beacon/...`) that Portal's Next.js server attaches
  the cookie's JWT to as an `Authorization` header.
- Refresh: a background call to `/api/auth/refresh` runs 5 min before
  expiry.
- Logout writes to Gatekeeper's revocation list (backed by DynamoDB).

SSO customers (Enterprise) go through WorkOS via Gatekeeper. See
INC-2026-05-19 for the last time that broke; the runbook is
`runbooks/rotate-workos-webhook-secret.md`.

## Data-fetching

Portal talks to two backend services directly:

- **Beacon** for all analytics reads (reports, cohorts, funnels).
  Client-side data fetching uses `@meridian/sdk` (a typed client
  generated from Beacon's OpenAPI spec).
- **Ledger** for the billing UI (plans, invoice list, current usage,
  seat management). Ledger is only reachable from the billing screens
  (`/app/settings/billing`).

Gatekeeper is called for login flows and for token refresh. Compass
is called during the first-time signup flow only.

## Shared packages (monorepo)

Portal lives in the `frontend/` monorepo. The relevant shared
packages:

- **`@meridian/ui`** — the design system. Buttons, form primitives,
  charts (built on top of Recharts), the layout shell. Also owns
  the theme tokens and Tailwind preset.
- **`@meridian/sdk`** — typed API client for Beacon (and, in the
  billing screens, Ledger). Generated from OpenAPI specs on the
  service side; regenerated in CI when the upstream service ships a
  spec change.
- **`@meridian/icons`** — SVG-sprite icon package.
- **`@meridian/tsconfig`** — shared base tsconfigs.

Portal itself owns:

- The Next.js app.
- Report-building UI (query builder, chart config).
- Billing screens (thin over Ledger endpoints).
- Team + workspace-settings screens.

## Routing structure

- `app/` — App Router entry.
  - `app/(marketing)/` — SSR public pages, no auth.
  - `app/(app)/` — CSR authenticated shell, middleware checks the
    session cookie.
  - `app/(app)/reports/[reportId]/` — the report viewer.
  - `app/api/` — server routes: `/api/auth/*`, `/api/proxy/*`.

## The Pages Router thing (please read)

**Legacy Pages Router routes still exist for `/settings/*`.** These
were written before the App Router migration and haven't been ported
yet. Concretely:

- `pages/settings/profile.tsx`
- `pages/settings/team.tsx`
- `pages/settings/api-keys.tsx`
- `pages/settings/notifications.tsx`

The router picks the Pages entry over any App Router `app/settings/*`
route today, so App Router shells for those paths are gated behind
the LaunchDarkly flag `portal.settings-app-router` (currently off
in prod, on in staging). Migration is in progress on Elena's team;
tracking issue `PROD-4118`.

Do **not** add new Pages Router routes. If you're adding a settings
page, put it under `app/(app)/settings/` and add the corresponding
Pages entry only if you need parity while the flag is off.

## Build + deploy

- `pnpm build` in CI; image pushed to ECR `meridian/portal`.
- ArgoCD app `portal-prod` watches the manifests in
  `deploy/portal/prod/`.
- Rollouts are canary: 10% → 50% → 100% over 15 min, gated on
  Datadog error-rate SLO.
