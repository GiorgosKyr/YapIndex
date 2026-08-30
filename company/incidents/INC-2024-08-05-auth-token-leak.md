---
title: "INC-2024-08-05: Auth tokens leaked into New Relic logs"
category: incident
author: Ben Ortiz
team: SRE
created: 2024-08-05
updated: 2024-08-06
status: resolved
version: 1.1
---

# INC-2024-08-05 — Auth tokens leaked into New Relic logs

- **Severity:** SEV-2
- **Status:** Resolved
- **Detected:** 2024-08-05 14:22 PT (21:22 UTC) via routine security review by Ravi
- **Resolved:** 2024-08-05 20:04 PT (2024-08-06 03:04 UTC)
- **Duration of exposure:** ~4 hours (10:15 PT – 14:19 PT)
- **PagerDuty:** PD-INC-A19442
- **Slack channel:** `#inc-2024-08-05`
- **Responders:** Ravi Patel (IC), Ben Ortiz (SRE), Marcus J. (Platform)

## Summary

While reviewing a New Relic log query for auth latency, Ravi noticed that a
subset of Gatekeeper log lines contained full JWTs (header + payload +
signature). The tokens were being emitted from a DEBUG code path in
`gatekeeper/handlers/session.go` that had been accidentally enabled in
`prod` earlier that morning via the LaunchDarkly flag `gk-verbose-session-log`
being flipped on for the `prod` environment (intended for `staging` only).

Any Meridian employee with access to New Relic could see the tokens. Log
retention in New Relic is 30 days. The tokens were valid access tokens for
customer sessions; if extracted before rotation they could be used to call
Beacon and Portal APIs on behalf of the affected users.

## Impact

- **Approx. tokens exposed:** ~11,400 unique JWTs across 47 workspaces.
- **Third-party exposure:** None confirmed. New Relic is SSO-gated (Okta),
  MFA required; no external log shipping was in place.
- **Customer impact:** Every active session was force-invalidated at 20:04 PT.
  Users had to re-authenticate. No known account takeovers.

## Timeline (all times PT)

- **10:15** — Marcus J. flips `gk-verbose-session-log` in LaunchDarkly. Intent
  was `staging`; `prod` was selected in the dropdown by mistake. Change not
  peer-reviewed (flag flips are not PR-gated).
- **10:16** — Gatekeeper pods begin emitting DEBUG log lines containing full
  JWTs on every `POST /v1/session/refresh` and `POST /v1/session/exchange`.
- **14:19** — Ravi, running a New Relic NRQL query for `service:gatekeeper
  AND level:debug`, sees `Bearer eyJhbGci...` in log output.
- **14:22** — Ravi opens `#inc-2024-08-05`, declares SEV-2, pages Ben.
- **14:27** — Marcus J. flips `gk-verbose-session-log` OFF in prod. New DEBUG
  lines stop. Existing log entries remain in New Relic.
- **14:40** — Decision to rotate all JWT signing keys and force
  re-authentication. Ravi owns comms; Ben owns rotation.
- **15:10** — New signing key generated, rolled to Gatekeeper via `kubectl
  rollout restart deploy/gatekeeper`. Old key kept in JWKS for grace period.
- **17:30** — DynamoDB `session-revocation-list` bulk-populated with all
  outstanding `jti`s. Beacon and Portal begin rejecting old tokens.
- **19:15** — Old JWT signing key removed from JWKS.
- **20:04** — All sessions confirmed invalidated. Incident closed.

## Mitigation

1. LaunchDarkly flag `gk-verbose-session-log` flipped off in prod.
2. All JWT signing keys rotated (`gk-jwt-sign-2024-08` retired).
3. All active sessions invalidated via revocation list.
4. New Relic log query saved and shared for future spot-checks.

## Follow-up

Full postmortem: `postmortems/2024-08-05-auth-token-leak.md`.

Action items are tracked in that document. This incident directly motivated
opening the Head of Security role (filled by Dara Okonkwo in Sept 2024).
