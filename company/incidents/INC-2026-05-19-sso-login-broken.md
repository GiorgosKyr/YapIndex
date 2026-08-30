---
title: "INC-2026-05-19: SSO login broken for WorkOS-backed enterprise workspaces"
category: incident
author: Dara Okonkwo
team: Security
created: 2026-05-19
updated: 2026-05-20
status: resolved
version: 1.0
---

# INC-2026-05-19 — SSO login broken (WorkOS webhook secret rotation)

- **Severity:** SEV-2
- **Status:** Resolved
- **Detected:** 2026-05-19 08:52 PT via customer ticket volume +
  `dd:monitor/62841` (`gatekeeper.sso.login_success_rate < 90%`)
- **Resolved:** 2026-05-19 11:47 PT
- **PagerDuty:** PD-INC-H01192
- **Slack channel:** `#inc-2026-05-19`
- **Responders:** Dara Okonkwo (IC, Security lead), Ravi Patel, Ben
  Ortiz (SRE), Lin Zhao (customer comms)

## Summary

At 05:31 PT on May 19, WorkOS rotated the webhook signing secret for
Meridian's production tenant per their scheduled quarterly rotation.
The rotation notice was sent by WorkOS to `security@getmeridian.com`,
a legacy address (see canon: legacy DNS `getmeridian.com` still
redirects but the mailbox was decommissioned in 2024). No one at
Meridian received the notice.

At the next SAML metadata refresh webhook (`connection.session_key_rotated`,
delivered 06:04 PT), Gatekeeper's `/webhooks/workos` handler rejected
the payload as "invalid signature" and returned 401. Gatekeeper
therefore did NOT refresh its cached SAML metadata for any customer
connection. Existing SSO sessions continued to work (JWTs already
issued), but any customer whose SSO session expired or who tried to
log in fresh got an "SSO connection failed — contact your admin"
error from the WorkOS callback handler.

## Impact

- **Enterprise workspaces affected:** 12 (all WorkOS-backed).
- **User-visible symptom:** unable to sign in via corporate IdP;
  password login not available on enterprise tier.
- **Duration:** first fresh-login failures at ~06:15 PT; resolved
  11:47 PT (~5.5h).
- **Data loss:** None.

## Timeline (PT)

- **05:31** — WorkOS rotates webhook signing secret. Notice sent to
  `security@getmeridian.com` (no active mailbox).
- **06:04** — First webhook after rotation
  (`connection.session_key_rotated`) arrives at
  `POST /webhooks/workos`. Gatekeeper computes HMAC with old secret,
  compares, mismatch, returns 401. Log line:
  `workos_webhook_verify_failed connection_id=conn_01H... status=401`.
- **06:15** — First enterprise user (at Nordwind Cycles) fails SSO
  login. WorkOS callback returns error, redirects to
  `/login?error=sso_connection_failed`.
- **07:30 – 08:45** — Trickle of ticket volume as European enterprise
  workspaces come online.
- **08:52** — `dd:monitor/62841` fires;
  Support flags to Dara.
- **09:00** — Dara joins `#inc-2026-05-19`, declares SEV-2.
- **09:20** — Root cause found: Gatekeeper `/webhooks/workos` logs
  show 100% 401 for the past ~3 hours. Cross-referenced with WorkOS
  dashboard showing "signing secret rotated 05:31 PT".
- **09:35** — Notice about rotation NOT in any Meridian inbox. Dara
  logs into WorkOS admin, finds notice history addressed to
  `security@getmeridian.com`.
- **09:50** — New webhook signing secret fetched from WorkOS admin,
  stored in AWS Secrets Manager as `gatekeeper/workos-webhook-secret`
  (existing path, rotated value).
- **10:20** — Gatekeeper deployment restarted to pick up new secret.
  Test webhook from WorkOS admin verifies successfully.
- **10:30** — Cached SAML metadata refreshed for all 12 connections
  via one-shot admin endpoint `POST /admin/workos/refresh-all`.
- **10:45** — First affected customer confirms SSO working again.
- **11:47** — Incident closed after all 12 workspaces confirmed
  operational.

## Mitigation

1. New WorkOS webhook signing secret installed in Secrets Manager.
2. Gatekeeper restarted; SAML metadata refreshed for all connections.
3. WorkOS notification contact updated to
   `security@meridiandata.io` (distribution list, not personal).

## Follow-up

- Action items tracked in Linear:
  - Sweep all vendor accounts (Stripe, WorkOS, Postmark, Datadog,
    PagerDuty, Sentry, LaunchDarkly) for lingering
    `@getmeridian.com` notification contacts.
  - Datadog monitor `dd:monitor/62901` added:
    `gatekeeper.webhook.workos.verify_fail_rate > 1%` for 5min.
  - Add a runbook `runbooks/rotate-workos-webhook-secret.md`.
- No formal postmortem for this SEV-2; findings are captured here
  and in the Security team weekly review notes.
