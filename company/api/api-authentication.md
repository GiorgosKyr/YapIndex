---
title: API Authentication
category: api
author: Dara Okonkwo
team: Security
created: 2025-04-30
updated: 2026-05-04
status: current
version: 2.4
---

# API Authentication

There are two distinct authentication paths for the Meridian API, and it
matters which one you use. Read/write endpoints authenticate as a **user
or M2M client** via a Gatekeeper-issued JWT. Ingest endpoints authenticate
as a **workspace** via a write key. This split exists because the
security model is different — ingest is a firehose scoped to one
workspace, while read/write is per-user with RBAC (see
`security/authorization.md`).

## JWTs (Bearer tokens)

JWTs are issued by **Gatekeeper**, our authoritative auth service (canon
§4). They're RS256-signed with keys stored in KMS
(`alias/gatekeeper-jwt`) and rotated annually — see
`security/authentication.md` for the full signing story and
`security/secrets-rotation.md` for rotation.

Access token TTL is **60 minutes**. Refresh tokens are valid for **30
days** and are stored in Redis (`meridian-sessions-prod`); revocation
lives in DynamoDB (`gatekeeper-revoked-jwt-ids`).

### Obtaining a token — human users

Portal signs users in via the normal browser flow (email/password with
optional MFA, or SSO — see below) and stores the resulting JWT in an
`HttpOnly` cookie. If you're building against the API from a Portal
context, the cookie is already set.

### Obtaining a token — M2M

For server-to-server integrations, use the OAuth 2.0 **client credentials**
grant against Gatekeeper:

```
POST https://auth.meridiandata.io/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=cli_...
&client_secret=<secret>
&scope=events:read reports:read reports:write
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "events:read reports:read reports:write"
}
```

Send the token as `Authorization: Bearer <access_token>` on subsequent
requests.

### SSO customers

Customers on Enterprise use **WorkOS SAML** (added 2025-Q4, canon §9).
After the SAML round-trip, Gatekeeper issues a JWT of the same shape as
above — from the API's perspective there is no difference. INC-2026-05-19
is a reminder that WorkOS webhook secret rotation must propagate to
Gatekeeper; see `security/secrets-rotation.md`.

## Write keys (ingest)

Write keys are workspace-scoped credentials for the ingest endpoints
(`POST /v3/events`, `POST /v3/events:batch`). They authenticate the
**workspace**, not a user. They're intended to be embedded in your
server-side code that emits events to Meridian.

- **Header:** `X-Meridian-Write-Key: mrdn_wk_...`
- **Rotation:** rotate via Portal → Admin → Write Keys. Old keys can be
  kept valid for up to 30 days while you cut over.
- **Do NOT embed in client-side JavaScript.** For browser-side ingest,
  use a public source key and the (soon to launch) Beacon token endpoint.
- **Storage:** the plaintext key is never persisted server-side after
  issuance — only a bcrypt hash lives in `api_write_keys` (see
  `database/postgres-schema.md`).

## Precedence and errors

If a request carries both a `Authorization: Bearer` header and
`X-Meridian-Write-Key`:

- On ingest endpoints, the write key is required and takes precedence.
- On all other endpoints, the JWT is required and the write key is
  ignored.

Errors follow the standard envelope (see `api/api-v3-reference.md`).
Common codes: `unauthenticated`, `invalid_token`, `expired_token`,
`invalid_write_key`, `write_key_revoked`.

## Related

- `security/authentication.md` (Gatekeeper deep-dive)
- `security/authorization.md` (RBAC and roles)
- `api/api-rate-limiting.md`
- `api/api-v3-reference.md`
