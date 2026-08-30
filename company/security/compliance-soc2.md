---
title: SOC 2 and Compliance Posture
category: security
author: Dara Okonkwo
team: Security
created: 2024-12-05
updated: 2026-05-30
status: current
version: 2.2
---

# SOC 2 and Compliance Posture

## SOC 2

Meridian achieved **SOC 2 Type II** certification in **November 2024**.
The audit covered the twelve months preceding, from November 2023
through October 2024, with the standard Trust Services Criteria (TSC)
of Security, Availability, and Confidentiality.

- **Auditor:** Prescient CPA (Seattle-based firm; engaged 2024-06).
- **Report period:** Nov 2023 – Oct 2024 (initial), Nov 2024 – Oct 2025
  (first renewal, completed 2026-01).
- **Next renewal:** the audit period ends 2026-10-31. The renewal
  engagement kicks off with Prescient in September 2026 and the
  refreshed Type II report is expected by end of Q1 2027.
- **Frequency:** annual renewal is the plan.

Reports are available under NDA — Sales requests them via the shared
`sales-security-reviews` Slack channel and Security fulfils.

## Controls tracking

All SOC 2 controls are tracked in **Vanta**. The Vanta integrations pull
evidence continuously from:

- AWS (via a read-only IAM role in each account, including
  `meridian-security`)
- GitHub (organisation-level app install)
- Datadog (monitoring evidence)
- PagerDuty (incident response evidence)
- Google Workspace (endpoint management, MFA enrolment)
- Vanta agents on employee laptops
- AWS Secrets Manager audit records (secret rotation — see
  `security/secrets-rotation.md`)

Vanta's dashboard is the single source of truth for control status. If
a control is red in Vanta, it is red — do not "fix" the report by
adjusting the scope.

## Framework scope

- **SOC 2 Type II** — in scope.
- **HIPAA** — **not in scope**. Meridian does not process Protected
  Health Information. Sales must not sign contracts that would put PHI
  into the platform. If a prospect asks, route to Dara.
- **PCI DSS** — not in scope. Card data is handled entirely by Stripe;
  we never see a PAN. Ledger integrates with Stripe Checkout / Elements
  so the browser posts card details directly to Stripe.
- **ISO 27001** — under consideration for 2027; not committed.

## GDPR and data residency

The EU/UK GDPR applies to a growing share of the customer base. Today,
all customer data is stored in `us-west-2`, and this is disclosed in
the DPA available on the website.

The **EU region buildout** (Frankfurt, `eu-central-1`) is in progress
in Q3 2026 (canon §11). Once live, Enterprise customers will be able to
elect EU data residency at workspace creation. Compass will route new
signups by region and Portal will show a residency badge. See
`architecture/multi-region-plan.md` for the detailed design.

Data subject request (DSR) handling — access, rectification, erasure —
is a manual workflow today owned by Support (Lin Zhao) with Security
review. Erasure of event data in ClickHouse uses partitioned
`ALTER ... DELETE`; the workflow is documented in
`runbooks/handle-dsr-request.md`.

## Vendor review

All new SaaS vendors that will process customer data or hold Meridian
production credentials go through a vendor security review before
procurement. Security signs off in Vanta.

## Related

- `security/authentication.md`
- `security/authorization.md`
- `security/secrets-rotation.md`
- `security/security-review-process.md`
