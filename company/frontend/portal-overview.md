---
title: Portal — Overview
category: frontend
author: elena.vasquez@meridiandata.io
team: Product Eng
created: 2024-06-11
updated: 2026-08-19
status: current
version: 6.0
---

# Portal

Portal is the customer-facing web app at `https://app.meridiandata.io`.
It's what customers mean when they say "the dashboard" or "the Meridian
UI." Internally people call it `meridian-portal` (the repo name) or just
"the app."

## Stack

- **Framework:** Next.js 14 (App Router).
- **Language:** TypeScript 5.4, strict mode on.
- **Runtime:** Node 20 on Vercel-compatible container images. Hosted on
  EKS, not Vercel — see `runbooks/portal-deploy.md`.
- **Design system:** `@meridian/ui` (Radix primitives + Tailwind CSS +
  `class-variance-authority`). See `frontend/design-system.md`.
- **Data layer:** `@meridian/sdk`, a typed client generated from the
  Beacon and Ledger OpenAPI specs. All fetches for server data go
  through it — no direct `fetch()` calls to internal APIs from
  components.
- **State:** Zustand for client, TanStack Query for server. See
  `frontend/portal-state-management.md`.
- **Auth:** Handled by Gatekeeper. See
  `frontend/portal-authentication.md`.

## Pages

Portal has been in the middle of a Pages Router → App Router migration
for most of 2026. Most pages have moved; Settings is the last holdout.

| Page       | Router      | Data source          |
|------------|-------------|----------------------|
| Dashboard  | App Router  | Beacon               |
| Reports    | App Router  | Beacon               |
| Cohorts    | App Router  | Beacon               |
| Alerts     | App Router  | Lighthouse + Beacon  |
| Billing    | App Router  | Ledger               |
| Settings   | Pages Router (WIP) | Multiple      |

Route directory layout (App Router pages):

```
app/
  (authed)/
    layout.tsx           # shell: nav, workspace switcher, feature flags
    dashboard/page.tsx
    reports/
      page.tsx
      [reportId]/page.tsx
    cohorts/
      page.tsx
      [cohortId]/page.tsx
    alerts/page.tsx
    billing/
      page.tsx
      invoices/[invoiceId]/page.tsx
  (public)/
    login/page.tsx
    signup/page.tsx
  api/
    healthz/route.ts
```

The `(authed)` group's `layout.tsx` reads the `mrdn_session` cookie in
its server component, calls Gatekeeper `/v1/session/introspect`, and
either renders the shell or redirects to `/login`.

## SDK usage

```ts
import { beacon } from '@meridian/sdk';

export default async function DashboardPage() {
  const overview = await beacon.metrics.get('workspace_overview', {
    range: 'last_7_days',
  });
  return <OverviewGrid data={overview} />;
}
```

The SDK is generated from OpenAPI at build time. Its types live in
`packages/sdk/src/generated/` and are checked in. Bumping an API version
means regenerating and cutting a new `@meridian/sdk` release.

## Auth flow (short version)

- Portal checks `mrdn_session` cookie on every server render.
- Absent or expired → redirect to Gatekeeper's `/authorize` with a
  callback URL back to Portal.
- Gatekeeper returns to Portal's `/auth/callback`, which sets the
  `mrdn_session` (12h) and `mrdn_refresh` (30d) httpOnly cookies.
- SSR requests to Beacon and Ledger forward `mrdn_session` as a Bearer
  token after exchanging it for a JWT server-side.

Full details and the SSO variant live in
`frontend/portal-authentication.md`.

## Feature flags

Portal reads flags from LaunchDarkly via a server-side evaluator at page
render, then hydrates the client. The list of active flags is exposed
under `/debug/flags` for internal accounts only (guarded by the
`is_meridian_staff` claim on the JWT).

## Related

- `frontend/design-system.md`
- `frontend/portal-state-management.md`
- `frontend/portal-authentication.md`
- `backend/beacon-service.md`
- `backend/ledger-service.md`
