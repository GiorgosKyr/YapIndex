---
title: Portal — State Management
category: frontend
author: elena.vasquez@meridiandata.io
team: Product Eng
created: 2024-09-22
updated: 2026-03-04
status: current
version: 2.1
---

# Portal state management

Portal separates client state from server state, and picks a different
library for each. This has been the pattern since the App Router
migration started in 2024, and it isn't up for renegotiation without a
new ADR.

- **Client state:** Zustand
- **Server state:** TanStack Query (react-query v5)
- **Not used:** Redux, MobX, Recoil, Jotai, RTK Query

If you're reading this because you're thinking about introducing Redux:
please read the ADR referenced at the bottom before you send a PR.

## Client state (Zustand)

Zustand stores hold UI-local state that must persist across route
changes but doesn't belong to the server: which cohorts are pinned in
the nav, whether the "compact rows" toggle is on, the last-used date
picker preset. Stores live under `src/stores/` and each exports a
single hook.

```ts
// src/stores/usePreferences.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type PrefState = {
  compactRows: boolean;
  defaultRange: 'last_24h' | 'last_7_days' | 'last_30_days';
  setCompactRows: (v: boolean) => void;
  setDefaultRange: (r: PrefState['defaultRange']) => void;
};

export const usePreferences = create<PrefState>()(
  persist(
    (set) => ({
      compactRows: false,
      defaultRange: 'last_7_days',
      setCompactRows: (v) => set({ compactRows: v }),
      setDefaultRange: (r) => set({ defaultRange: r }),
    }),
    { name: 'mrdn.preferences.v1' }
  )
);
```

Stores that persist across sessions use `zustand/middleware`'s `persist`
into `localStorage`. Anything workspace-scoped is namespaced with the
workspace slug in the key so switching workspaces doesn't leak state.

Stores that must NOT persist (mostly transient modal or drag state) use
plain `create` with no middleware.

## Server state (TanStack Query)

Every call into Beacon, Ledger, Compass, or Lighthouse from the client
side goes through TanStack Query. The `QueryClient` is set up once in
the root App Router client boundary:

```ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,   // 5 minutes
      gcTime: 30 * 60 * 1000,
      retry: (failureCount, err) =>
        !isAuthError(err) && failureCount < 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

Five minutes of `staleTime` is deliberate — most dashboards read data
that Beacon-Aggregator itself caches for at least that long. A shorter
`staleTime` was tried in early 2025 and just moved cost into the
network layer without giving customers fresher numbers. See
`backend/beacon-caching.md` for why five minutes is safe.

Query keys are structured as `[resource, workspaceId, ...params]`. On
workspace switch, we invalidate everything keyed under the previous
`workspaceId` in one call.

## Loading and error states

- **Route-level loading:** Every App Router page has a sibling
  `loading.tsx` that renders the same skeleton shape as the real page,
  so the layout doesn't reflow when data arrives.
- **Error boundaries:** Every top-level route has an `error.tsx` that
  logs the error to Sentry with tags `route`, `workspace_id`, and
  `user_id`, then renders a "something went wrong" panel with a
  "reload" button that calls `router.refresh()`.
- **In-page errors:** For per-widget errors (a single failing chart
  in a dashboard), the widget renders its own inline error state and
  reports the error to Sentry with an additional `widget_id` tag. It
  does not bubble to the route error boundary.

## What we do NOT store client-side

- The bearer token used to call Beacon/Ledger — those are httpOnly
  cookies and never touch JS.
- Any customer-scoped PII beyond what's needed to render the current
  view. In practice this means no long-lived email/user tables in
  Zustand.

## Related

- `frontend/portal-overview.md`
- `frontend/portal-authentication.md`
- `adrs/0039-portal-no-redux.md`
