---
title: General FAQ
category: support
author: Lin Zhao
team: Support
created: 2024-06-11
updated: 2026-08-01
status: current
version: 6.1
---

# Meridian — General FAQ

Answers to the things we get asked most often. If you don't find your
question here, try `support/faq-billing.md` or `support/faq-api.md`,
or email `support@meridiandata.io`.

## Getting started

### How do I invite a teammate?

In Portal, go to Settings → Members → Invite. Enter their email, pick
a role (Admin, Editor, Viewer), and hit Send. They'll get an email from
`no-reply@meridiandata.io` with a signup link that expires in 7 days.

Seat limits depend on your plan — see
[Pricing tiers](../product/pricing-tiers.md).

### How do I create an API write key?

Settings → API Keys → New Key. Choose "Write" scope, name it (we
recommend naming per environment, e.g. `prod-shopify-writer`), and
copy the key immediately — you can't view it again after leaving the
page. Rotate keys any time from the same screen.

Read-only keys are separate. If you need a key for our query API,
create it as a "Read" key.

### How do I set up a workspace for a second brand?

Growth, Scale, and Enterprise plans support multiple workspaces.
From the org switcher in the top-left, click "Create workspace." Each
workspace has its own event stream, dashboards, members, and API keys.

Starter is capped at 1 workspace.

## Data & events

### Why can't I see events I just sent?

Events flow through ingest → Kafka → enrichment → ClickHouse. In steady
state, an event that hits our ingest endpoint shows up in Portal in
about **8 seconds at the median and up to 45 seconds at the 99th
percentile**. If you're still not seeing anything after ~1 minute:

1. Check that you're using a **write** API key, not a read key.
2. Check the response code from the ingest endpoint — it should be
   `202 Accepted`.
3. Confirm the `workspace_id` in the payload matches the workspace
   you're viewing (a common mix-up on multi-workspace organizations).
4. Check the "Live events" debugger under Data → Live.

If Live shows nothing at all, open a ticket with the API request/response
and we'll trace it.

### How is my data retained?

**25 months** on all plans, unless you're on a custom Enterprise
retention (up to 60 months). After 25 months, events roll off
ClickHouse. Aggregate reports built before roll-off remain queryable.

Exports to your own warehouse via Atlas are unaffected — anything you've
exported is yours to retain.

### What's an MTE?

Monthly Tracked Event. One enriched event that lands in our storage
counts as one MTE. See
[the billing FAQ](faq-billing.md) for the fiddly bits.

### Can I delete events (for GDPR/CCPA)?

Yes. Settings → Privacy → Data Subject Requests. Paste the user
identifier (whatever you send us as `user_id`), and we'll issue a
delete across ClickHouse and any exports on the next Atlas run
(nightly). Confirmation email once complete — typically < 24h.

## Reports & dashboards

### Why is my dashboard slow?

99% of "slow dashboard" reports come down to a very wide date range
combined with a high-cardinality property (e.g. `user_id`) as a
group-by. Try narrowing the window or removing the group-by. If it's
still slow, the Beacon team wants to hear about it.

### Can I share a dashboard with someone outside my organization?

Not yet. This is on the roadmap but not committed. For now, the export
buttons (PNG, CSV) work — or add them as a Viewer to the workspace.

## Access & security

### How do I enable SSO?

SSO/SAML is an Enterprise-tier feature via WorkOS (Okta, Azure AD,
Google Workspace). Contact your CSM to enable — the setup takes
about 30 minutes and requires an admin on your IdP.

### I got locked out — how do I reset?

Use the "Forgot password" link on the login page. If SSO is enabled
for your workspace, password reset is disabled — you'll need to reset
through your IdP.

### Can I audit who did what in my workspace?

Yes. Settings → Audit Log (Growth and above). CSV export available.
Enterprise gets 12 months of audit history; other plans get 90 days.

## Everything else

### Do you have a status page?

`status.meridiandata.io`. Subscribe there for incident notifications.

### How do I contact support?

- Starter/Growth/Scale: `support@meridiandata.io`.
- Enterprise: your named CSM, or the Slack Connect channel.
- Response times: see [customer tiers](customer-tiers.md).

### Is there a community?

We run a Slack community — `meridiandata.io/community` for the invite
link. About 800 members, mostly practitioners at other Meridian
customers.
