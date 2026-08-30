---
title: Authorization (RBAC)
category: security
author: Dara Okonkwo
team: Security
created: 2024-12-02
updated: 2026-05-11
status: current
version: 2.4
---

# Authorization

Meridian uses **role-based access control** scoped per workspace, with
policy decisions centralized in Gatekeeper. Callers (Portal, Beacon,
Ledger, Relay, ...) do not enforce authorization locally beyond a thin
capability check — they ask Gatekeeper via a gRPC `Authorize` call and
follow its decision.

Roles are per (user, workspace). A single user can be an Owner of one
workspace and a Viewer of another.

## Roles

| Role | Typical use | Notable permissions |
|---|---|---|
| **Owner** | Founding admin. Exactly one per workspace. | Everything Admin can do, plus delete workspace and transfer ownership. |
| **Admin** | Ops/IT lead. | Manage members, roles, API/write keys, SSO config, integrations. Cannot delete workspace. |
| **Editor** | Analyst who builds/publishes reports. | Create, edit, run reports, cohorts, alerts. Manage webhooks. |
| **Analyst** | Analyst who explores but doesn't publish. | Run existing reports, save personal drafts. Cannot publish. |
| **Viewer** | Consumer of dashboards. | Read-only access to published reports and cohorts. |
| **Billing** | Finance contact. | Read invoices, update payment method, download usage reports. No product data access. |

The Billing role is deliberately orthogonal — Ledger calls it out
because Finance contacts often shouldn't see event data. In Ledger docs
this is referred to as the "account billing contact"; the underlying
record is the same `workspace_members` row.

## Policy engine

Authorization policies are expressed as **Open Policy Agent** (Rego)
bundles, versioned in the `meridian-policies` repo and pulled by
Gatekeeper on startup and every 60 seconds thereafter. Rego was chosen
so policies are testable in CI and reviewable independently of
Gatekeeper deploys.

A typical policy fragment:

```rego
package meridian.reports

default allow := false

allow if {
    input.action == "reports:read"
    role := data.roles[input.subject.workspace_id][input.subject.user_id]
    role in {"owner", "admin", "editor", "analyst", "viewer"}
}

allow if {
    input.action == "reports:write"
    role := data.roles[input.subject.workspace_id][input.subject.user_id]
    role in {"owner", "admin", "editor"}
}
```

## The `Authorize` gRPC call

Callers send:

```
Authorize({
  subject:      { user_id, workspace_id, roles, sso },
  action:       "reports:write",
  resource_id:  "rep_...",  // optional, for row-level checks
  request_id:   "req_..."
})
```

Gatekeeper responds `{ allow: bool, reason: string }`. The `reason`
field is for logging only; do not surface it to end users verbatim.

**Caching:** the client library caches decisions for **30 seconds** per
`(user_id, workspace_id, action, resource_id)` tuple. This is a
deliberate trade-off: after a role change, the affected user may still
see the old permissions for up to 30 seconds. Admin-visible role edits
in Portal display a warning message reflecting this.

## Write keys

Write keys authenticate a workspace, not a user, and grant a fixed
scope: ingest events into that one workspace. There are no roles for
write keys. They can be issued, listed, and revoked by Owners and
Admins.

## Auditing

Every `Authorize` decision is logged (structured) to Datadog with
`decision`, `subject.user_id`, `subject.workspace_id`, `action`, and
`resource_id`. Retention is 90 days for standard workspaces and 400
days for Enterprise (contract requirement).

## Related

- `security/authentication.md`
- `api/api-authentication.md`
- `security/security-review-process.md`
