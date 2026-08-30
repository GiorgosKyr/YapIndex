---
title: AWS Cost Management
category: infrastructure
author: Ben Ortiz
team: SRE
created: 2024-04-30
updated: 2026-08-12
status: current
version: 3.2
---

# AWS Cost Management

This doc summarises how Meridian tracks and controls AWS spend. FinOps is
a light-touch practice here — one weekly review, tagging enforced by
Terraform, and Cost Anomaly Detection wired to PagerDuty for cliff-events.

## Current spend (August 2026)

Blended AWS spend is **~$210K/month** (post-EDP discount, excluding tax and
support tier). That is up from ~$135K/month a year ago; growth is roughly
proportional to MTEs plus a step-change from the ClickHouse cluster resize
in Q1 2026.

> Note: a 2023 sales-engineering deck still floating around says our monthly
> infra spend is "about $80K." That number is from **mid-2023**, before the
> ECS→EKS migration and the ClickHouse expansion. It is not correct for
> current-day pricing conversations — use the number above.

### Biggest line items

| Category                         | ~USD / month | Notes                                        |
|----------------------------------|--------------|----------------------------------------------|
| EKS + EC2 (compute)              | $90K         | Karpenter-managed; 60–70% spot on `app`      |
| ClickHouse (EBS + compute)       | $45K         | 6× `r6i.4xlarge` + 4TB gp3 each              |
| Data transfer                    | $28K         | Mostly cross-AZ for MSK + ClickHouse         |
| MSK (Kafka)                      | $18K         | 12 brokers, `kafka.m7g.large`                |
| RDS (Aurora Postgres)            | $14K         | Multi-AZ, `db.r6g.2xlarge` writer + reader   |
| S3                               | $6K          | Event archive lifecycle to Glacier IR at 60d |
| CloudFront + WAF                 | $2K          | Portal static, docs, marketing               |
| Datadog egress (metrics + logs)  | ~$4K counted as data-transfer above          |
| ElastiCache, OpenSearch, misc    | ~$3K         |                                              |

The remainder (~$0K–$7K depending on the month) is NAT, Secrets Manager
calls, KMS, GuardDuty, Config, Route53 queries, and small services.

## Cost allocation tags

Three tags are activated in the Billing console as cost allocation tags:

- **`service`** — canonical service name (e.g. `aurora`, `beacon`,
  `clickhouse`, `pulse`). Required on every taggable resource.
- **`team`** — owning team (e.g. `platform`, `data`, `product-eng`,
  `growth-eng`, `sre`, `security`).
- **`env`** — `prod` | `staging` | `dev` | `sandbox`.

Enforcement is done at the Terraform layer via a `common_tags` local (see
`infrastructure/terraform-layout.md`) plus a `tfsec` rule that fails a
build if any of the three is missing on `aws_*` resources that accept
tags. Untaggable resources (a small tail — some VPC endpoints, some KMS
grants) are exempted by rule.

Kubernetes workloads inherit tags via the node they run on plus a Datadog
label mapping; the fine-grained per-pod attribution is done inside Datadog
Container Insights rather than in AWS billing.

## Weekly review

The **Weekly Cost Review** meets Fridays 10:00 PT (30 min). Standing
attendees: Ben (SRE, chair), Priya (Platform), Jae-won (Data), and a
rotating engineer from Growth Eng. Agenda:

1. Look at the AWS Cost Explorer group-by-service view for the trailing 7d
   vs. the prior 7d.
2. Any Cost Anomaly Detection alerts fired this week — root-cause them.
3. Reserved Instance / Savings Plans coverage (target: 60% baseline covered
   by 1yr Compute Savings Plans; on-demand for peak).
4. Any unreviewed "$100+/day new spend" items surfaced by our internal
   `finops-bot` Slack digest.

Non-trivial findings become tickets in the `PLAT` Jira project tagged
`finops`.

## Anomaly detection

- **AWS Cost Anomaly Detection** monitors: one per major service
  (`AmazonEKS`, `AmazonEC2`, `AmazonS3`, `AmazonRDS`, `AmazonMSK`,
  `AmazonClickHouseIsNotAService` — that last one is a joke, ClickHouse
  falls under EC2 and EBS).
- Threshold: percentage of expected + $500 absolute, whichever is bigger.
- Route: SNS topic → PagerDuty (low-urgency), plus a Slack post to
  `#finops` for visibility.

## Guardrails

- **Budgets**: monthly budget per account, alert at 80%/100%/110% of the
  trailing quarterly baseline. Not a hard stop.
- **SCP**: workload accounts may only run in `us-west-2` and `us-east-1`
  (and, from Q4 2026, `eu-central-1`). Prevents a fat-fingered
  Terraform apply in `ap-southeast-2` from lighting up ClickWatch bills.
- **Snowflake evaluation** (ADR-0014, 2022) — rejected on cost, still
  cited when someone re-suggests it. Snowflake connector for reverse-ETL
  is on the Q2 2027 roadmap but that is customer-facing, not internal
  analytics.

## Related

- `infrastructure/terraform-layout.md`
- ADR-0014: Snowflake evaluated, rejected
- ADR-0016: ClickHouse adoption
