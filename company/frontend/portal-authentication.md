---
title: Portal — Authentication Flow
category: frontend
author: dara.okonkwo@meridiandata.io
team: Security
created: 2025-01-15
updated: 2026-06-04
status: current
version: 3.0
---

# Portal authentication

Portal never issues its own tokens. Every authentication decision is
made by Gatekeeper. Portal's job is to (a) get the user to Gatekeeper,
(b) hold the resulting cookies, and (c) forward them to backend calls.
For the underlying token contract (JWT claims, refresh semantics,
revocation), see `security/authentication.md`.

## Cookies used

| Cookie          | Contains                | Attributes                                | Lifetime |
|-----------------|-------------------------|-------------------------------------------|----------|
| `mrdn_session`  | Opaque session id       | httpOnly, Secure, SameSite=Lax, Domain=`.meridiandata.io` | 12 hours |
| `mrdn_refresh`  | Opaque refresh handle   | httpOnly, Secure, SameSite=Lax, Domain=`.meridiandata.io` | 30 days  |
| `mrdn_ws`       | Currently selected workspace slug | httpOnly=false, Secure                | 30 days  |

`mrdn_session` and `mrdn_refresh` are never readable from JavaScript.
`mrdn_ws` is client-readable because the workspace switcher UI needs it
before the first server render.

## Standard login (email + password)

```
User → Portal /login
Portal → 302 → Gatekeeper /authorize
  ?client_id=portal
  &redirect_uri=https://app.meridiandata.io/auth/callback
  &state=<csrf>
Gatekeeper renders its own login form (Portal never sees the password).
Gatekeeper → 302 → Portal /auth/callback?code=<one-shot>&state=<csrf>
Portal server:
  - Verifies state.
  - Exchanges code for {session_id, refresh_handle} at Gatekeeper /token.
  - Sets mrdn_session (12h) and mrdn_refresh (30d) cookies.
Portal → 302 → /dashboard (or the originally requested URL).
```

Once the cookies are set, every SSR page render calls Gatekeeper's
`/v1/session/introspect` server-side with `mrdn_session`, which returns
a short-lived JWT that Portal then uses in the `Authorization: Bearer`
header when calling Beacon or Ledger from that same render. The JWT is
never sent to the browser. This means a leaked cookie is bounded by
session lifetime, and revocation on Gatekeeper takes effect on the next
introspect call (max 60s later, since introspect responses are cached
per-pod).

## SSO customers (WorkOS)

Enterprise-tier customers can be SSO-only. In that case Portal must
route the login through WorkOS, not the standard Gatekeeper login form.
The routing hint is a query string on `/login`:

```
https://app.meridiandata.io/login?workspace_slug=buoyant-apparel
```

The `/login` page reads `workspace_slug`, looks up
`GET https://gk.internal.meridian.internal/v1/workspaces/{slug}/auth-method`
server-side, and if the answer is `sso`, redirects to
`/authorize?workspace_slug=...&connection=workos`. Gatekeeper then
initiates the SP-initiated SAML flow through WorkOS. Callback lands
back at Portal `/auth/callback` and the cookies are set exactly the
same way as the standard flow.

The WorkOS routing was rolled out with the Enterprise-tier launch in
Q4 2025. It's what INC-2026-05-19 broke — a WorkOS webhook secret
rotation was applied on WorkOS's side but not propagated to
Gatekeeper's secret store, and SSO logins failed for about 3 hours
until the secret was re-synced.

## Refresh

A pre-render middleware
(`src/middleware/refresh.ts`) checks `mrdn_session` on every request.
If the session is within 60 seconds of expiry (or already expired),
and `mrdn_refresh` is present, the middleware calls Gatekeeper
`/v1/session/refresh` with the refresh handle. Gatekeeper returns a
new session id; the middleware rewrites the cookie and lets the
request continue.

If refresh fails (expired refresh handle, revoked user, etc.), both
cookies are cleared and the response is a 302 to `/login`.

## Logout

`POST /auth/logout` on Portal:

1. Calls Gatekeeper `/v1/session/revoke` with `mrdn_session`.
2. Clears `mrdn_session` and `mrdn_refresh` in the response.
3. 302 to `/login`.

Gatekeeper writes the revocation to its DynamoDB revocation list
(see `security/authentication.md`).

## Related

- `security/authentication.md` — token contract and revocation.
- `frontend/portal-overview.md`
- `incidents/INC-2026-05-19-workos-sso-broken.md`
