---
title: Engineering Onboarding — Day 1
category: onboarding
author: Marcus Oduya
team: Eng
created: 2023-06-01
updated: 2026-05-04
status: current
version: 3.1
---

# Day 1 checklist

Welcome to Meridian. This is meant to get you productive by end of day 1.
Your buddy (assigned below) is your first-line question channel for the
next two weeks — don't feel bad about pinging them.

## Before you touch anything

- [ ] IT has shipped you a **MacBook Pro (M-series)**. Sign in with your
      Meridian Google account (you should have creds in the welcome email).
- [ ] Turn on **FileVault** if it isn't already. Security has a nightly
      check that will page Dara if it's off after 24h.
- [ ] Install **1Password** and log in.

## Accounts (Okta is the front door)

You should have gotten a Welcome to Okta email. Everything below is behind
Okta SSO — if any tile is missing, ping `#it-help` on Slack.

- [ ] **Okta** — confirm MFA is set up (WebAuthn preferred; TOTP fallback).
- [ ] **Google Workspace** (mail, calendar, drive).
- [ ] **Slack** — join at least these channels:
      `#general`, `#eng`, `#eng-oncall`, `#incidents`, `#platform`,
      `#deploys`, `#random`, plus your team channel.
- [ ] **GitHub** — accept the invite to the `meridian-data` org. Add your
      SSH key. Enable 2FA (WebAuthn).
- [ ] **PagerDuty** — you'll get added to schedules later, but confirm you
      can log in.
- [ ] **Datadog**, **Sentry**, **ArgoCD**, **AWS SSO** (all via Okta tile).
- [ ] **Linear/Jira** — we use Jira for eng tickets. Look up your team
      project (e.g. `ENG`, `PLAT`, `SEC`, `DATA`).
- [ ] **LaunchDarkly** — read-only for most, write access via team lead.

## Laptop setup

Follow `laptop-setup.md`. It'll take 45–90 minutes depending on your
internet. The `brew bundle` step is the long one — start it, get lunch,
come back.

## Your buddy

Your manager will assign a buddy on your first morning and drop the intro
in Slack. Buddies are usually someone on the same team who's been here
6–18 months. Expected time commitment from them: a 30-min daily check-in
for the first week.

If you haven't heard by 11:00 local, ping your manager. If your manager is
out, ping `#eng` and someone will grab it.

## First reads (before end of day)

- `company/company-overview.md`
- `company/history.md`
- Your team's `README.md` in the top-level services repo
- The current on-call schedule for your rotation (App or Platform)

## What to expect on day 2

You'll do a repo walkthrough with your buddy, get access to the dev
cluster, and ideally get a "hello world" PR merged — anything from a
typo fix to a small doc improvement. See `eng-onboarding-week-1.md` for
the rest of week 1.

## Getting stuck

Escalation order:
1. Buddy
2. Team channel
3. Your manager
4. `#eng`
5. `#it-help` (accounts / hardware only)

Do not sit stuck for more than 30 minutes on day 1. That's a rule.
