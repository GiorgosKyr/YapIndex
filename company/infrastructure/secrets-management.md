---
title: Secrets Management
category: infrastructure
author: Dara Okonkwo
team: Security
created: 2024-10-11
updated: 2026-06-01
status: current
version: 2.1
---

# Secrets Management

AWS Secrets Manager is the primary store for all runtime secrets at Meridian.
Secrets are surfaced into Kubernetes through the **External Secrets Operator
(ESO)**, which reconciles `ExternalSecret` custom resources into native
`Secret` objects. Applications read them via env vars or mounted files —
they do not talk to Secrets Manager directly.

A few classes of material do not live in Secrets Manager: Gatekeeper's JWT
signing keys are in KMS (asymmetric), TLS cert private keys are in ACM
(never exported), and a small tail of legacy config sits in SSM Parameter
Store (see "Legacy" below).

## Naming convention

Path style, forward-slash separated:

```
<env>/<service>/<key>
```

Examples:

- `prod/ledger/stripe-api-key`
- `prod/gatekeeper/workos-webhook-secret`
- `prod/aurora/kafka-sasl-password`
- `staging/relay/hmac-signing-key`
- `prod/atlas/snowflake-user-password` (planned Q2 2027)

Rules:

- One secret per key. Do not stuff a JSON blob with ten fields into one
  secret unless the fields rotate together (e.g. a full DB credential).
- Env prefix is always `prod`, `staging`, `dev`, or `sandbox` — matches
  the Kubernetes namespace prefix so ESO's ClusterSecretStore selection is
  trivially scoped.
- Kebab-case for the leaf key.

## External Secrets Operator

ESO runs cluster-wide, one instance per cluster, with IRSA for a role that
can `secretsmanager:GetSecretValue` under the matching env prefix only.

Example `ExternalSecret` for Ledger's Stripe key:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ledger-stripe
  namespace: growth
spec:
  refreshInterval: 15m
  secretStoreRef:
    name: aws-prod
    kind: ClusterSecretStore
  target:
    name: ledger-stripe
    creationPolicy: Owner
  data:
    - secretKey: STRIPE_API_KEY
      remoteRef:
        key: prod/ledger/stripe-api-key
```

`refreshInterval` is 15 minutes for most secrets and **1 minute** for
Gatekeeper's WorkOS webhook secret (that shorter interval was added after
INC-2026-05-19, when a webhook-secret rotation took an hour to propagate).

## Rotation

Rotation policy is documented in **`runbooks/rotate-production-secrets.md`**.
In short:

- **Stripe** keys: rotated quarterly by the Growth team, tracked in a
  security Jira board.
- **Aurora RDS master password**: rotated automatically by Secrets Manager
  every 60 days (managed rotation function).
- **MSK SASL credentials**: rotated manually every 90 days; there's a
  Datadog monitor for age > 100 days.
- **WorkOS webhook secret**: rotated on WorkOS's schedule (~90d) and
  mirrored into Secrets Manager by an internal Lambda within 60s.
- Any secret leaked in a log → rotate within 24h. Post-INC-2024-08-05
  we added Datadog log-pattern monitors for JWT-shaped strings and Stripe
  key prefixes.

## Gatekeeper JWT keys (KMS)

Gatekeeper signs its JWTs with an **asymmetric KMS key**:

- Alias: `alias/gatekeeper-jwt`
- Key spec: `RSA_2048`
- Usage: `SIGN_VERIFY`
- Only Gatekeeper's IRSA role can `kms:Sign`; Beacon, Ledger, Portal, and
  Relay have `kms:GetPublicKey` for local verification. There is a JWKS
  endpoint at `https://auth.meridiandata.io/.well-known/jwks.json` for
  external verifiers.
- The key rotates annually via a new KMS key + `kid` header bump; the
  previous key is retained for 90 days to cover long-lived refresh tokens.

The private key material never leaves KMS. There is no way to export it,
which is the point.

## Legacy: SSM Parameter Store

Before Secrets Manager (early 2024), we used SSM Parameter Store
`SecureString` values. A handful of legacy parameters still live there,
mostly used by scheduled Lambdas that predate ESO adoption:

- `/legacy/atlas/snowflake-account-name` — not a secret really, but it
  moved with the batch.
- `/legacy/relay/twilio-*` — Twilio was removed in 2024; parameters can
  be deleted but nobody has claimed the ticket.

Migration ownership: Platform is walking the list quarterly; target is
"all gone by end of 2026." The `pillar-eng` doc has the tracking spreadsheet.

## Related

- `runbooks/rotate-production-secrets.md`
- `postmortems/2024-08-05-auth-token-log-leak.md`
- `postmortems/2026-05-19-workos-webhook-rotation.md`
- ADR-0037: External Secrets Operator adoption
