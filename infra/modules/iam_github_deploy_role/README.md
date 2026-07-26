# Module: iam_github_deploy_role

The IAM role GitHub Actions assumes via OIDC (no static keys, ADR-0003).
**One instance per environment** (ADR-0021); the identity provider it trusts is
created once by `iam_github_oidc_provider`.

Lives in the `bootstrap-oidc` state level, never in an environment's own state,
so a `terraform destroy` cannot delete the permissions it is running with
(ADR-0015).

## Trust scope

Audience is always `sts.amazonaws.com`. Subjects are assembled from:

- `repo:<owner>/<repo>:ref:refs/heads/<branch>` — only when
  `trust_branch_ref = true`;
- `repo:<owner>/<repo>:environment:<e>` for each `github_environments` entry.

`trust_branch_ref` **must be false for any environment protected by required
reviewers.** A branch subject is assumable by any workflow running on that
branch, which routes around the approval gate the GitHub Environment exists to
provide. Stage keeps it; prod does not.

An empty subject list is rejected by a precondition rather than producing a
trust policy nothing can satisfy — that failure would otherwise surface as an
opaque STS error at the next login.

## Deploy policy scope

Resource-scoped where cheap and meaningful:

- S3 state bucket (read/write to that bucket only);
- DB secret (`secretsmanager:GetSecretValue` on the `<name_prefix>-db-credentials-*`
  pattern only);
- IAM management restricted to exactly `<name_prefix>-ecs-execution` and
  `<name_prefix>-ecs-task`. The role cannot modify itself, which is what
  ADR-0015 traded away and got back.

Infrastructure-management actions (ec2/elb/ecs/ecr/rds/logs/budgets/cloudwatch)
use `"*"` resources on purpose: Terraform creates and destroys many short-lived
resources each cycle whose ARNs are not known in advance. Deliberate demo
trade-off, not a production posture.

Because every scoped ARN is derived from `name_prefix`, the stage instance
grants nothing over prod resources and vice versa.
