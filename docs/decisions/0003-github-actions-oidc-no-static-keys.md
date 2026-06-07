# ADR-0003: GitHub Actions OIDC for AWS access (no static keys)

## Status
Accepted (Phase 0)

## Context
CI/CD must deploy into the demo account from GitHub Actions. Storing static AWS
access keys in GitHub Secrets is a long-lived credential that can leak and must
be rotated. GitHub Actions supports OIDC federation, letting a workflow assume
an IAM role with short-lived credentials and no stored secrets.

## Decision
GitHub Actions authenticates to AWS via OIDC: the workflow exchanges its OIDC
token for an assumed IAM deploy role in the demo account. No static AWS access
keys are stored in GitHub. The OIDC provider and deploy role are created by
Terraform (module `iam_github_oidc`).

## Decision details
- Trust policy restricts the role to a specific repository owner/repo and, where
  practical, branch (`UVE-QA/aws-devops-sdet-demo`, branch `main`).
- The deploy role is least-privilege, demo-scoped: S3 state, ECR, ECS, RDS,
  logs, budgets, `secretsmanager:GetSecretValue` on the DB secret ARN, and
  `iam:PassRole` scoped to the ECS task/execution roles.
- GitHub stores only non-secret values (region, role ARN, TF_VAR_* identifiers).

## Consequences
- No long-lived AWS credentials in CI; nothing to rotate or leak.
- Chicken-and-egg: Actions cannot assume a role that does not exist yet, so the
  role must be created by a local apply first (see ADR-0014).
- Terraform remote state shared between local and CI requires the role to have
  S3 state access (see ADR-0004).
