# Module: iam_github_oidc

Creates the GitHub OIDC identity provider and the IAM deploy role that GitHub
Actions assumes via OIDC (no static keys, ADR-0003). Created by the FIRST local
`terraform apply` of the environment (ADR-0014), because Actions cannot assume a
role that does not yet exist.

## Trust scope

The role can be assumed only by workflows in
`repo:<github_owner>/<github_repo>:ref:refs/heads/<github_branch>`
(default branch `main`), with audience `sts.amazonaws.com`.

## Deploy policy scope

Resource-scoped where cheap and meaningful:
- S3 state bucket (read/write to the bucket ARN only).
- DB secret (`secretsmanager:GetSecretValue` on the secret ARN only).
- IAM role management and `iam:PassRole` restricted to `${name_prefix}-*` roles.

Infrastructure-management actions (ec2/elb/ecs/ecr/rds/logs/budgets/cloudwatch)
use `"*"` resources on purpose: Terraform creates and destroys many short-lived
resources each cycle whose ARNs are not known in advance. This is a deliberate
demo trade-off, not a production posture. Tightening to resource-level ARNs is a
Phase 8 hardening item.

## OIDC thumbprint

`thumbprint_list` is set to GitHub's known root CA thumbprint
(`6938fd4d98bab03faadb97b34396831e3780aea1`). Modern AWS validates the GitHub
OIDC endpoint against trusted CAs, so the thumbprint is largely a formality, but
verify it is still current at first apply (Phase 6) and update if GitHub rotates.
