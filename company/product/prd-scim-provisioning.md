---
title: SCIM 2.0 Provisioning for Enterprise SSO
category: prd
author: Sam Whitfield
team: Product
created: 2026-05-20
updated: 2026-08-05
status: draft
version: 0.4
---

# PRD: SCIM 2.0 Provisioning

**Target ship:** Q4 2026
**Owners:** Sam Whitfield (Product); Dara Okonkwo (Security, consulting)
**Related:** `product/prd-eu-region.md`, `security/sso-enterprise.md`

## Problem

Since the WorkOS-backed SSO/SAML launch in 2025-11, Enterprise customers
have repeatedly asked for automated user provisioning. Today, an admin
must manually invite each user via Portal after that user has been
granted access in the customer's IdP (Okta, Azure AD, Google Workspace).
This creates:

- **Drift.** When an employee is offboarded in Okta, they remain a
  member of the Meridian workspace until an admin remembers to remove
  them. Two Enterprise customers have flagged this as a compliance
  blocker; one (Forge Athletics) escalated in their QBR.
- **Rollout friction.** New Enterprise deployments hit long user-add
  cycles (finance teams of 40+ people, invited one at a time).
- **Support burden.** L2 support has taken 27 tickets in the last quarter
  that boil down to "why do I still see terminated users in my
  workspace?"

## Goals

- Ship a compliant SCIM 2.0 endpoint on Gatekeeper:
  `https://scim.meridiandata.io/scim/v2/`, per RFC 7644.
- Support `Users` and `Groups` resources with the standard CRUD verbs
  (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
- Group membership drives Meridian role assignment. Mapping is
  configured per workspace by the workspace admin (e.g. Okta group
  `meridian-admins` → Meridian role `admin`).
- Validated integration with Okta and Azure AD at GA. Google Workspace
  best-effort.
- Bearer-token auth per workspace. Tokens are rotatable from Portal
  under Settings → SSO → Provisioning.

## Non-goals

- SCIM for non-Enterprise tiers (Starter/Growth/Scale) — this is an
  Enterprise-only feature per pricing.
- Deprovisioning of active sessions on user delete. Sessions expire via
  Gatekeeper's normal TTL (1h access token). We will document the
  time-to-revoke clearly; adding forced session termination is a
  Q1 2027 candidate.
- Just-in-time provisioning via SAML assertions (a common request, but
  a separate approach — not part of this PRD).
- Password/secret management. SCIM users are always federated.

## Proposed solution

New service? No — SCIM lives inside Gatekeeper. Dara has been clear
that expanding the auth surface into a separate service creates more
attack surface than it removes. The SCIM handlers become a new module
inside `gatekeeper` (Go).

**Gatekeeper user-model changes (dependency):**

- Users get a stable `external_id` field for the IdP's canonical ID.
- Group membership becomes a first-class relation (currently roles are
  attached directly to users; groups are implicit).
- Audit log gains SCIM-origin events (`user.provisioned`, `user.deprovisioned`,
  `user.group_changed`).

These changes are non-trivial and are on the critical path. See
`architecture/gatekeeper-user-model-v2.md` (draft).

Portal gets a Settings → SSO → Provisioning panel: base URL, token
management, group→role mapping UI, and a "last sync" indicator.

Docs plan: `docs.meridiandata.io/enterprise/scim`, with vendor-specific
setup guides for Okta and Azure AD.

## Risks

- **Gatekeeper user-model migration.** Non-trivial Postgres migration
  on the `users`, `roles`, and new `groups` tables. Requires downtime
  window or careful expand-contract. Priya's team has scoped this at
  4 weeks.
- **WorkOS relationship.** WorkOS offers Directory Sync (their own SCIM
  proxy). We evaluated it and decided to own SCIM directly because we
  need Meridian-native group→role mapping. This is a considered choice;
  we accept the operational cost.
- **Rate limits.** IdPs can burst thousands of ops during initial sync.
  Gatekeeper needs a per-workspace SCIM rate limiter separate from the
  general API limits.

## Open questions

- Do we require SCIM for the EU region at GA, or is US-only for SCIM
  acceptable at first? Currently leaning US-first, EU-follow.
- Pricing: SCIM is bundled into Enterprise. Do Scale customers get a
  paid add-on? Sam: no, keep it as an Enterprise-tier differentiator.
