---
title: Authentication (Gatekeeper)
category: security
author: Dara Okonkwo
team: Security
created: 2024-11-04
updated: 2026-06-20
status: current
version: 3.2
---

# Authentication

**Gatekeeper** is Meridian's authoritative authentication service. Every
API request that presents a JWT — regardless of which product surface it
targets — is validated by Gatekeeper (directly for the Portal and Beacon
gRPC paths, or via the shared middleware library that ships with a
signed JWKS bundle).

Some older documents (particularly 2022-era design docs) refer to this
service as `identity-service`. Same service. It was renamed to
Gatekeeper in 2023 as part of the post-Great-Extraction cleanup.

## JWTs

- **Algorithm:** RS256.
- **Signing keys:** stored in AWS KMS under the alias
  `alias/gatekeeper-jwt`. The private key never leaves KMS — Gatekeeper
  signs by calling `kms:Sign`.
- **Key rotation:** KMS auto-rotate is enabled — this happens annually.
  Older key versions remain valid for the lifetime of any outstanding
  token they signed (max 30 days for refresh tokens).
- **JWKS:** published at `https://auth.meridiandata.io/.well-known/jwks.json`,
  cached by all consumers for 10 minutes.
- **Claims:** standard (`iss`, `sub`, `aud`, `exp`, `iat`, `jti`) plus
  `workspace_id`, `roles` (array), and `sso` (bool).

## Token lifetimes

- **Access token:** 60 minutes.
- **Refresh token:** 30 days. Stored server-side in Redis
  (`meridian-sessions-prod` — see `database/redis-usage.md`); the client
  holds only an opaque cookie/handle.
- **Revocation:** the JWT `jti` is written to DynamoDB
  (`gatekeeper-revoked-jwt-ids`, see `database/dynamodb-usage.md`) on
  explicit logout, admin revocation, or incident response.

## SSO

WorkOS handles SAML for Enterprise customers (added 2025-Q4, canon §9).
After a successful SAML assertion, Gatekeeper mints a JWT of the same
shape as password-authenticated tokens with the `sso: true` claim set.

Reminder from INC-2026-05-19: WorkOS webhook secrets are part of the
quarterly rotation set (`security/secrets-rotation.md`). Missing that
propagation broke Portal login for SSO customers for ~2 hours.

## MFA

Time-based one-time passwords (TOTP) are supported for all users.
Enrolment happens in Portal → Settings → Security.

- **Optional** for Editor, Analyst, Viewer, Billing roles.
- **Required** for the Admin role (and always for Owner).

Enforcement is at Gatekeeper: an Admin without an enrolled TOTP factor
cannot obtain an access token, only a "step-up-required" partial token
that Portal understands and uses to redirect to enrolment.

WebAuthn/passkeys are on the Q4 2026 roadmap, but not shipped.

## Password policy

- Minimum 12 characters.
- Checked against the Have-I-Been-Pwned k-anonymity API on set/change.
- Rate-limited to 5 attempts/minute per email + 20/minute per IP.
- Hashed with Argon2id (memory 64 MiB, iterations 3, parallelism 1).

## Service-to-service

Internal services authenticate to each other via short-lived JWTs
minted by Gatekeeper for a service account (mTLS handles transport;
the JWT carries the principal). No static bearer tokens between
services in production.

## Related

- `security/authorization.md` — RBAC and Open Policy Agent
- `security/secrets-rotation.md`
- `api/api-authentication.md`
- `database/dynamodb-usage.md`
- `database/redis-usage.md`
