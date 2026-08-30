---
title: "ADR-0058: Use WorkOS for SAML/SSO"
category: adr
author: Dara Okonkwo
team: Security
created: 2025-09-04
updated: 2025-09-22
status: Accepted
version: 1.0
---

# ADR-0058: Use WorkOS for SAML/SSO

## Context

Enterprise tier launch in 2025-Q4 requires SAML SSO (with SP-init and
IdP-init flows), SCIM (Q4 2026), and directory sync. Sales has three
active deals blocked on SSO support (~$540K ARR combined).

Gatekeeper today handles our own OAuth-style token issuance, MFA via
TOTP, and basic user/workspace membership. Extending it to be a full SP
for arbitrary customer IdPs (Okta, Azure AD, Ping, JumpCloud, Google
Workspace) is a substantial project — every IdP has quirks and we'd own
metadata refresh, cert rotation, signature validation, edge cases.

## Decision

Adopt **WorkOS** as our SSO provider. WorkOS sits in front of Gatekeeper:

1. Customer configures IdP through WorkOS admin portal (or via our
   API-driven flow in Portal).
2. Portal login sends SSO customers to `/sso/login?workspace_slug=...`
   which redirects to WorkOS.
3. WorkOS handles the SAML dance with the customer's IdP.
4. WorkOS calls back to Gatekeeper's `POST /sso/workos/callback` with a
   signed profile.
5. Gatekeeper issues a normal Meridian JWT with SSO claims.

Gatekeeper still owns:
- JWT issuance and validation (RS256, KMS-managed keys).
- Session lifecycle and revocation.
- MFA policy for non-SSO users.
- RBAC (SSO doesn't change our authorization model).

## Alternatives considered

- **Build in-house.** Rejected — 6+ months of engineering, ongoing IdP
  quirk maintenance. Not a competitive differentiator.
- **Auth0.** Feature-rich but the enterprise pricing scales badly for
  our per-tenant model, and we don't want to depend on it for password-
  based auth (which we already handle).
- **Okta Workforce Identity.** Overkill; Okta as a customer's IdP works
  the same through WorkOS.

## Consequences

**Positive:**
- ~4-6 weeks to production instead of ~6 months.
- WorkOS handles IdP compatibility matrix.
- SCIM 2.0 in-scope on the same platform (Q4 2026).

**Negative:**
- New vendor in the critical auth path — outage there breaks SSO logins.
  Non-SSO logins unaffected.
- Vendor lock-in for SSO configuration data.
- Cost: ~$0.125 per SSO user / month (predictable).

## Operational notes

- WorkOS **webhook signing secret** rotates. Gatekeeper stores it in
  Secrets Manager at `prod/gatekeeper/workos-webhook-secret`. See
  [runbook](../runbooks/rotate-production-secrets.md).
- **Note (2026-05):** we hit exactly this rotation issue in
  [INC-2026-05-19](../incidents/INC-2026-05-19-sso-login-broken.md) —
  new secret wasn't propagated in time. Rotation runbook updated after.

## Status

Accepted 2025-09-22. Live 2025-11-14 alongside Enterprise tier GA.
