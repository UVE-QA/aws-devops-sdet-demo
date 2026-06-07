# ADR-0001: Dedicated AWS Organizations member account for the demo

## Status
Accepted (Phase 0)

## Context
The demo deploys real billable infrastructure (ECS, ALB, RDS). It runs inside
an existing AWS Organization that also contains a management account and other
project accounts. Mixing workload resources with the management account (which
owns billing, Organizations, and IAM Identity Center) is a blast-radius and
security risk, and makes cost attribution and clean teardown harder.

## Decision
Deploy all workload resources into a dedicated AWS Organizations member account
(`993912191738`), in OU Projects. Never deploy workload into the management
account (`029280391941`). Region: us-west-2.

## Consequences
- Clear cost attribution: everything billable lives in one account, easy to
  audit and to tear down.
- Smaller blast radius: a mistake in the demo cannot touch org-level config.
- Every `terraform apply`/deploy must verify caller identity resolves to the
  demo account before proceeding (guard against wrong-account deploys).
- Human access and machine access into this account are defined separately
  (see ADR-0002, ADR-0003).
