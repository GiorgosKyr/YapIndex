---
title: Billing FAQ
category: support
author: Lin Zhao
team: Support
created: 2024-08-02
updated: 2026-07-18
status: current
version: 5.4
---

# Billing FAQ

Answers about invoices, payment methods, plans, and MTEs. For account
and workspace management see the [general FAQ](faq-general.md).

## Invoices & charges

### Why did my invoice change from last month?

Almost always one of three reasons:

1. **You went over your MTE allowance.** Overages are billed on the
   next invoice at your plan's per-1,000 rate. Growth includes 2.5M
   MTEs; Scale includes 15M. If you had a traffic spike, that's the
   first thing to check.
2. **A prorated plan change.** If you upgraded or added seats mid-cycle,
   the invoice includes a prorated line for the partial month, plus
   the new full amount going forward.
3. **Tax rate changed** (Stripe Tax handles this automatically based on
   your billing address).

You can see the breakdown in Portal under Settings → Billing → Invoices,
or on the PDF invoice itself.

### What is an MTE?

Monthly Tracked Event — one enriched event that lands in our storage
per calendar month. Events that fail validation (bad schema, missing
required fields) don't count. De-duplicated events (same `event_id`
seen more than once) count only once.

The counter for your account resets on the first of your billing
cycle. You can view live MTE usage in Portal under Settings → Billing
→ Usage.

### Can I get a refund?

Refunds are handled case by case. In general:

- If we made a billing error, absolutely — contact `billing@meridiandata.io`
  and we'll credit or refund promptly.
- If you were affected by the **November 2024 duplicate-charge incident**,
  please contact `billing@meridiandata.io` if you haven't already
  received the correction — we credited affected accounts within 5
  business days of the incident but a small number of edge cases may
  have slipped through.
- If you're canceling mid-cycle, we don't prorate refunds by default
  (monthly plans). Annual plans, contact CSM.
- If you're on Enterprise, your MSA governs.

### Why do I see two charges from Stripe?

Some banks show a temporary authorization hold in addition to the
actual capture. The hold falls off in a few days. If both charges
persist for more than 5 business days, contact us with the last 4
digits of the card and the amounts.

## Payment methods

### How do I update my payment method?

Portal → Settings → Billing → Payment method → Update. This uses
Stripe's hosted card entry — we never see your card details directly.
Supports Visa, Mastercard, Amex, and SEPA direct debit for EU accounts.

For ACH (US bank transfer), Enterprise-tier only, contact your CSM.

### Can I pay by invoice / net-30?

Enterprise annual contracts only. Contact `billing@meridiandata.io`
or your CSM.

### The card on file is expired — what happens?

Stripe retries automatically for 7 days after a failed charge. If it
still fails, the account moves to a **grace period** for another 7
days, during which Portal shows a banner and API keys keep working.
After 14 days total, the account is suspended (ingest still accepts
events for 72h so you don't lose data, but Portal is read-only).

Update the card any time to resume.

## Plans & upgrades

### How do I upgrade or downgrade?

Portal → Settings → Billing → Change plan. Upgrades take effect
immediately (prorated). Downgrades take effect at the next renewal.

If you're moving between Enterprise custom plans, that's a CSM
conversation.

### Do you offer annual pricing?

Yes — 15% off list for annual pre-pay. Multi-year contracts (2y+)
get 20%+ depending on volume, negotiated by sales.

### Are there non-profit or startup discounts?

Yes, case by case. Email `sales@meridiandata.io` with a bit of context.

## Tax & compliance

### Do you charge sales tax / VAT?

Yes, where required. Stripe Tax handles this based on your billing
address. If you have a valid VAT ID or resale certificate, add it in
Settings → Billing → Tax info and the charge will be zero-rated where
applicable.

### Where are your invoices from?

Meridian Data, Inc. (US), Seattle WA. EU customers still contract with
the US entity for now — an EU entity is being evaluated but not yet in
place. Even after the EU region launches (Q4 2026), billing continues
from the US entity initially.

### Do you provide W-9 / tax forms?

Yes. `billing@meridiandata.io`.

## Anything else

For anything billing-related that isn't answered here, please email
`billing@meridiandata.io`. Enterprise customers can also reach out
via their Slack Connect channel.
