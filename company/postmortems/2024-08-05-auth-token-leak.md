---
title: "Postmortem: Auth tokens leaked into New Relic logs (2024-08-05)"
category: postmortem
author: Ravi Patel
team: Security (interim), SRE
created: 2024-08-22
updated: 2024-08-28
status: current
version: 1.0
---

# Postmortem — 2024-08-05: Auth tokens leaked into New Relic logs

> Related incident: `incidents/INC-2024-08-05-auth-token-leak.md`
> Blameless postmortem. We describe what the system allowed to happen,
> not who to blame. Names appear as responders and owners only.

## Summary

On 2024-08-05 from 10:15 PT to 14:19 PT, Gatekeeper wrote full JWTs
(header, payload, signature) to New Relic logs for every session
refresh and exchange request in production. Approximately 11,400
unique tokens were exposed. The tokens were visible to any Meridian
employee with New Relic access (SSO + MFA gated, no external log
shipping). We rotated all signing keys, invalidated all outstanding
sessions, and removed the log lines from further retention windows
where possible. No unauthorized access was detected.

## Impact

- Exposure window: ~4 hours 4 minutes.
- Tokens exposed: ~11,400 across 47 workspaces.
- External exposure: none observed.
- Customer-visible: forced re-authentication for every active user at
  20:04 PT. Customer comms went out as a proactive advisory the
  following morning (Aug 6) via `security@meridiandata.io`.
- Regulatory: no GDPR/CCPA notification triggered per our privacy
  counsel — no PII beyond user_id/email exposed, and no evidence of
  exfiltration.

## Timeline (PT)

- **10:15** — LaunchDarkly flag `gk-verbose-session-log` toggled on
  in the "prod" environment. The intended environment was "staging".
- **10:16** — Gatekeeper begins emitting DEBUG log lines containing
  full JWTs from `handlers/session.go:issueTokenLog()`.
- **14:19** — Discovered during ad-hoc NRQL query.
- **14:22** — Incident channel `#inc-2024-08-05` opened; SEV-2.
- **14:27** — Flag disabled.
- **15:10 – 19:15** — Key rotation and revocation-list population.
- **20:04** — All sessions invalidated; incident closed.

Full minute-by-minute in the incident doc.

## Root cause

The Gatekeeper session code path had a DEBUG-level log statement
that included the raw JWT for engineering diagnostics. The log
statement was guarded only by log level; log level was in turn
controlled by a LaunchDarkly flag. That flag could be flipped for
any environment by any engineer with the LaunchDarkly editor role
(all of engineering).

Three system properties combined to allow the incident:

1. **Sensitive data was ever loggable.** The code was allowed to
   pass a raw JWT to `logger.Debug()`. There was no guard against
   this at compile time or lint time.
2. **A production log level was runtime-toggleable without review.**
   No change management, no PR, no peer approval was required to
   change log verbosity in prod.
3. **The LaunchDarkly environment dropdown defaults to "prod".**
   The UI does not require an extra confirmation for prod-scoped
   changes to sensitive flags.

## Contributing factors

- **Missing dedicated security ownership.** At the time, Gatekeeper
  was informally owned by SRE with review by the CTO. No one had
  the full-time job of catching this kind of pattern in review or
  audit. (See action item on hiring a Head of Security.)
- **Log query patterns weren't part of routine ops.** The leak was
  found by a curious ad-hoc query, not by a monitor. Nothing in our
  observability stack alerts on "sensitive-looking string in logs".
- **New Relic retention default.** 30 days by default; we hadn't
  set a shorter retention on `service:gatekeeper`.

## What went well

- Detection-to-declaration was under 3 minutes.
- Rotation ran cleanly; the revocation-list flow (built for a
  hypothetical breach case) worked as designed.
- Customer comms drafted by 18:00 PT, sent morning of Aug 6, honest
  and specific.
- No production customer-facing service degraded during rotation —
  the JWKS grace period allowed for a seamless key roll.

## What went poorly

- The DEBUG code path existed at all. It should not have been
  possible for a runtime configuration change to cause secret
  material to be logged.
- No monitor caught it. We got lucky.
- The LaunchDarkly change was a single-click prod change with no
  peer approval and no audit alerting.
- We had no runbook for "tokens leaked to logs" — the response was
  improvised, competently, but improvised.

## Action items

| # | Owner | Description | Status | Due |
|---|-------|-------------|--------|-----|
| 1 | Ravi | **Never log tokens.** Enforce via a `pre-commit` hook and static-analysis rule (`grep`-style + a semgrep rule) that flags any log call whose formatted string could include `token`, `jwt`, `authorization`, `bearer`, or a JWT-shaped value. | done | 2024-09-05 |
| 2 | Ben | Remove the DEBUG code path from Gatekeeper entirely. Replace with structured, redacted logging (`jti` and `user_id` only, never the full token). | done | 2024-08-30 |
| 3 | Nadia / Ravi | **Hire dedicated Head of Security.** Own future auth review, threat modeling, incident response for security-class incidents. | done | 2024-09 (Dara Okonkwo joined 2024-09-16) |
| 4 | Ben | New Relic retention on `service:gatekeeper` logs reduced to 7 days. Consider shorter or drop-at-source for auth services. | done | 2024-08-20 |
| 5 | Priya | LaunchDarkly: sensitive flag list defined; changes to those flags require peer-approval mode enabled. `gk-*` flags added to the list. | done | 2024-09-10 |
| 6 | Dara (post-hire) | Standing quarterly log-content audit: sample 10k lines per service, scan for secrets. First run: 2024-Q4. | recurring | 2024-Q4 first pass |
| 7 | Dara | Write `runbooks/rotate-jwt-signing-keys.md` capturing the actual steps used in this incident. | done | 2024-10-08 |

## References

- `security/authentication.md` — updated 2024-10 to reflect these
  changes (no-token-in-logs, JWKS rotation procedure).
- `security/logging-standards.md` — new doc created 2024-09-22.
- LaunchDarkly flag policy: `security/launchdarkly-flag-policy.md`.
