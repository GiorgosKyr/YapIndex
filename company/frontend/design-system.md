---
title: "@meridian/ui — Design System Overview"
category: frontend
author: Elena Vasquez
team: Product Eng
created: 2024-02-11
updated: 2026-05-30
status: current
version: 3.2
---

# @meridian/ui

Meridian's shared component library, published to our internal npm registry
(`https://npm.mrdn.io`) as `@meridian/ui`.

## Stack

- **Primitives:** [Radix UI](https://www.radix-ui.com) (unstyled, accessible).
- **Styling:** Tailwind CSS 3.4 + `class-variance-authority` for variants.
- **Icons:** `lucide-react` (subset re-exported as `@meridian/ui/icons`).
- **Types:** TypeScript strict, no `any` in public API.

Bundled with `tsup` (ESM only). Peer deps: `react@^18`, `react-dom@^18`.

## Design tokens

Tokens live in `packages/ui/src/tokens.css` and are exposed as CSS custom
properties prefixed `--mrdn-`:

```css
:root {
  --mrdn-color-primary:    hsl(238 82% 60%);   /* indigo */
  --mrdn-color-accent:     hsl(174 62% 47%);
  --mrdn-color-danger:     hsl(0 72% 51%);
  --mrdn-color-bg:         hsl(0 0% 100%);
  --mrdn-color-fg:         hsl(222 18% 12%);
  --mrdn-radius-sm:        4px;
  --mrdn-radius-md:        8px;
  --mrdn-font-sans:        "Inter", ui-sans-serif, system-ui, sans-serif;
  --mrdn-font-mono:        "JetBrains Mono", ui-monospace, monospace;
}
```

Dark mode via `[data-theme="dark"]` on `<html>` (Portal sets it based on user
preference or system default).

## Components (partial list)

`Button`, `Input`, `Select`, `Combobox`, `Dialog`, `Popover`, `Tooltip`,
`Table`, `Tabs`, `Toast`, `Card`, `Badge`, `Sparkline`, `MetricTile`,
`DateRangePicker`, `CohortSelector`, `AlertBanner`.

The chart primitives (`Sparkline`, `LineChart`, `BarChart`) wrap `recharts`
under the hood, but that's an implementation detail — consumers should not
import `recharts` directly.

## Storybook

Published at `https://ui.mrdn.io` (VPN-required internal domain). CI job
`.github/workflows/ui-storybook.yml` builds and deploys on every merge to
`main` of `meridian/ui`.

## Contribution process

1. Open a PR against `meridian/ui`.
2. Attach a Loom or screenshot for any visual change.
3. Request review from `@meridian/design-system-owners` (currently Elena
   Vasquez + two Product Eng ICs — see `CODEOWNERS`).
4. Any new public component needs a Storybook entry, unit tests
   (Testing Library), and an a11y check (Axe passes).
5. Major changes require a design review with Elena's team; async in
   `#design-system` or sync in the Wednesday design sync.

## Versioning

SemVer. We are currently on `3.x`. `4.0` will drop `Tokens.legacy.*` and
migrate to the newer color scale — RFC in `docs.mrdn.io/rfcs/ui-4`.

## Consumers

- Portal (`meridian/portal`) — primary consumer.
- Compass onboarding UI (`meridian/compass-web`).
- Internal admin console (`meridian/admin`) — pinned to `2.x`, migration
  tracked in `ENG-3910`.
