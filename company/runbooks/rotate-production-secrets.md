---
title: Rotate Production Secrets
category: runbook
author: Ben Ortiz
team: SRE
created: 2024-07-11
updated: 2026-05-14
status: current
version: 3.2
---

# Rotate Production Secrets

This is the **authoritative** procedure for rotating production secrets at
Meridian Data. It supersedes `runbooks/rotate-secrets-legacy.md` (archived
2024-07), which described the Jenkins/SSM-Parameter-Store flow.

Covered secrets:

1. Stripe API key (`prod/ledger/stripe-api-key`)
2. Postgres/Aurora passwords (`prod/<service>/db-password`)
3. WorkOS webhook secret (`prod/gatekeeper/workos-webhook-secret`)
4. JWT signing key — KMS-managed (`prod/gatekeeper/jwt-signing-key`)
5. Datadog API key (`prod/platform/datadog-api-key`)

## Preconditions

- You are on-call primary or have been explicitly delegated by `@sre-primary`.
- You have the `SecretsRotator` IAM role assumed via SSO
  (`aws sso login --profile meridian-prod-sre`).
- You have `kubectl` context `arn:aws:eks:us-west-2:...:cluster/meridian-prod`.
- External Secrets Operator (ESO) is healthy:
  `kubectl -n external-secrets get pods` — all `Running`.
- A rotation ticket exists in Linear (`SEC-####`) with change window logged.

## Steps

### 1. Stripe API key (Ledger)

1. In Stripe Dashboard → Developers → API keys, click **Roll key** on the
   restricted key `rk_live_ledger_prod`. Copy the new value.
2. Push to Secrets Manager:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id prod/ledger/stripe-api-key \
     --secret-string "$NEW_STRIPE_KEY" \
     --profile meridian-prod-sre
   ```
   Expected output:
   ```json
   {
     "ARN": "arn:aws:secretsmanager:us-west-2:...:secret:prod/ledger/stripe-api-key-xXxXxX",
     "VersionId": "a1b2c3d4-...",
     "VersionStages": ["AWSCURRENT"]
   }
   ```
3. ESO reconciles within 60s. Confirm:
   ```bash
   kubectl -n ledger get externalsecret ledger-stripe -o jsonpath='{.status.refreshTime}'
   ```
4. Trigger a Ledger pod refresh (ESO does not auto-restart pods):
   ```bash
   kubectl -n ledger rollout restart deploy/ledger-api
   ```

### 2. DB passwords (Postgres)

For each affected service (Aurora, Beacon, Ledger, Gatekeeper, Compass,
Cartograph, Portal):

1. Rotate on the RDS side:
   ```bash
   aws rds modify-db-instance \
     --db-instance-identifier meridian-prod-pg \
     --master-user-password "$NEW_PW" --apply-immediately
   ```
2. Update Secrets Manager:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id prod/<service>/db-password \
     --secret-string "$NEW_PW"
   ```
3. Rolling-restart each consuming Deployment.

### 3. WorkOS webhook secret (Gatekeeper)

1. In WorkOS Dashboard → Webhooks → **Rotate signing secret**. Copy value.
2. `aws secretsmanager put-secret-value --secret-id prod/gatekeeper/workos-webhook-secret --secret-string "$NEW_SECRET"`
3. Roll Gatekeeper: `kubectl -n gatekeeper rollout restart deploy/gatekeeper`.
4. **Do not** click "Revoke old secret" in WorkOS until step 5 verification
   passes. INC-2026-05-19 was caused by prematurely revoking.

### 4. JWT signing key (KMS-managed)

The JWT signing key lives in KMS as an asymmetric CMK
(`alias/gatekeeper-jwt-signer`). Rotation is a **key version bump**, not a
value swap.

1. `aws kms create-key --key-usage SIGN_VERIFY --customer-master-key-spec RSA_2048`
   → note the new `KeyId`.
2. Update Secrets Manager pointer:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id prod/gatekeeper/jwt-signing-key \
     --secret-string "{\"kid\":\"<new-kid>\",\"key_id\":\"<KeyId>\"}"
   ```
3. Gatekeeper publishes the new `kid` in its JWKS within 60s. Old `kid` is
   retained for 24h to allow in-flight tokens to validate.

### 5. Datadog API key

1. Datadog → Organization Settings → API Keys → **Rotate**.
2. `aws secretsmanager put-secret-value --secret-id prod/platform/datadog-api-key --secret-string "$NEW_DD_KEY"`
3. `kubectl -n datadog rollout restart daemonset/datadog-agent`.

## Verification

For each secret rotated:

- Service `/healthz` returns 200 with the new key version stamped in headers.
- No 401/403 spike in Datadog dashboard `platform / secrets rotation`.
- Ledger: run `scripts/stripe-smoke.py` — must return `charge.succeeded`.
- Gatekeeper: fetch `https://auth.meridiandata.io/.well-known/jwks.json` —
  new `kid` present.

## Rollback

Every `put-secret-value` creates a new version. To roll back:

```bash
aws secretsmanager update-secret-version-stage \
  --secret-id prod/<service>/<key> \
  --version-stage AWSCURRENT \
  --move-to-version-id <previous-version-id> \
  --remove-from-version-id <current-version-id>
```

Then restart the affected Deployment.

## Contacts

- Primary: `@sre-primary` in `#eng-oncall`
- Security lead: Dara Okonkwo (`@dara`)
- Escalation: Ben Ortiz (SRE lead), then Ravi Patel (CTO)
