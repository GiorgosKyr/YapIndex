---
title: Meeting notes — API v3 launch readiness review
category: meeting-notes
author: Elena Vasquez
team: Product Eng
created: 2025-05-15
updated: 2025-05-15
status: current
version: 1.0
---

# 2025-05-15 — API v3 launch readiness

Launch date: **2025-05-20** (Tuesday).
Zoom, 45 min.

## Attendees
- Elena Vasquez (Product Eng, chair)
- Sam Whitfield (Product)
- Ravi Patel (CTO)
- Marcus Oduya (VP Eng)
- Tomás Herrera (Growth Eng — Ledger uses the v2 client internally)
- Lin Zhao (Support)
- Priya Ramanathan (Platform)
- Ben Ortiz (SRE) — partial
- Wen Liu (Ingest) — partial

## Recap of what v3 changes vs v2
- **Cursor pagination** (was offset). Legacy offset still works on v2
  endpoints; v3 is cursor-only.
- **ISO-8601 timestamps everywhere**. v2 accepted epoch seconds in
  several endpoints — silently converted. v3 rejects with 400.
- **`workspace_id` moved to the request body**, out of the
  `X-Workspace-Id` header. Header still accepted on v2.
- **Error envelope changed**: v2 returned `{ "error": "...", "code": N }`;
  v3 returns `{ "error": { "code": "SNAKE_CASE", "message": "...", "details": {...} } }`.
- New endpoint set for cohorts (`/v3/cohorts/*`) with saved-cohort semantics.

## Discussion

- Sam: docs site (`docs.mrdn.io`) is updated, v3 tab is the default, v2
  tab is present with a "will be deprecated" banner.
- Elena: SDKs — JS, Python, Go all cut to `2.0.0` (they follow their own
  SemVer). Node SDK has a compat layer that translates v2 calls
  transparently for 6 months.
- Tomás: Ledger's internal use of the v2 client (for enforcement of
  usage limits) — we'll move to v3 by end of June. Not a launch blocker.
- Marcus: **v2 EOL date**. Discussion. Proposal: **2026-05-20** (one
  year post-launch). Agreed as the initial public date. Everyone
  acknowledges this is likely to slip once — we'll extend once, hard
  stop the second time.
- Lin: Support prep — playbook drafted, macro updated. She wants a
  Slack channel for the first 2 weeks (`#api-v3-launch`) that Support
  can drop weird customer issues into. Elena: yes, will create.
- Ravi: what about the customers on the "we integrated once in 2021
  and haven't touched it since" tier? Sam: we identified 47 accounts
  making zero v3-compatible calls. Outreach starts Monday. AM-led,
  not sales-led.
- Priya: infra — no changes needed. v3 lives on the same Beacon
  deployment behind a version-prefixed route.
- Ben: rollout — no phased rollout needed for v3 endpoints (they're
  additive). For v2 deprecation, follow the standard deprecation runbook.
- Wen: does Aurora need to know about v3? No — Aurora is ingest, this
  is all query-side. Wen leaves the call.

## Risks flagged
- Timezone bugs in the ISO-8601 change. Elena: fuzz tests added, but
  keep an eye on Sentry for `iso8601 parse` errors in the first 48h.
- Error envelope change might break customer error-handling code that
  string-matches the old shape. Docs call it out explicitly; support
  macro references it.

## Action items
- [ ] Elena — create `#api-v3-launch` channel (today)
- [ ] Elena — final go/no-go post in `#eng` Monday EOD 2025-05-19
- [ ] Sam — send customer email blast Monday morning
- [ ] Tomás — Ledger internal migration to v3 client, target 2025-06-27
- [ ] Lin — send Support playbook to `#support`, add to onboarding wiki
- [ ] Marcus — set calendar reminder for 2026-01: revisit v2 EOL date
      (2026-05-20 target)
- [ ] Ben — add v2 traffic dashboard, share link in `#api-v3-launch`

## Next meeting
- Retrospective: 2025-06-12 (3 weeks post-launch)
