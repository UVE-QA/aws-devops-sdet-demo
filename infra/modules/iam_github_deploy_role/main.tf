# GitHub Actions deploy role — ONE INSTANCE PER ENVIRONMENT (ADR-0021).
#
# Trusts the OIDC provider created by iam_github_oidc_provider; it does not
# create a provider itself, so this module can be instantiated more than once
# in the same account.
#
# The deploy policy is least-privilege and demo-scoped, keyed entirely off
# name_prefix, so a prod instance grants nothing over stage resources and vice
# versa. Lives in the bootstrap-oidc state level, never in an environment's
# state, so a destroy run cannot delete the permissions it is running with
# (ADR-0015).

data "aws_caller_identity" "current" {}

locals {
  repo_ref = "repo:${var.github_owner}/${var.github_repo}"

  # A branch subject lets any workflow on that branch assume the role directly.
  # That is what makes the stage role usable from a push-triggered job — and
  # exactly what must NOT exist for prod, where the GitHub Environment's
  # required reviewers are the approval gate. A branch subject would route
  # straight around them.
  trust_subjects = concat(
    var.trust_branch_ref ? ["${local.repo_ref}:ref:refs/heads/${var.github_branch}"] : [],
    [for e in var.github_environments : "${local.repo_ref}:environment:${e}"],
  )
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.trust_subjects
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${var.name_prefix}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.trust.json

  tags = {
    Name = "${var.name_prefix}-github-deploy"
  }

  lifecycle {
    # An empty subject list produces a trust policy nothing can satisfy, which
    # fails at the next OIDC login with an opaque STS error rather than here.
    precondition {
      condition     = length(local.trust_subjects) > 0
      error_message = "iam_github_deploy_role: no trust subjects. Set trust_branch_ref = true or provide at least one entry in github_environments."
    }
  }
}

# Least-privilege, demo-scoped deploy policy. Resource-level scoping is applied
# where it is cheap and meaningful (state bucket, DB secret, the two ECS roles);
# the infrastructure-management actions (network/alb/ecs/rds/logs/budgets) use
# "*" because Terraform creates and destroys many short-lived resources whose
# ARNs are not known ahead of time in a repeatable cycle. This is a deliberate
# demo trade-off, documented in README.md.
data "aws_iam_policy_document" "deploy" {
  statement {
    sid       = "TerraformStateBucket"
    actions   = ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = [var.state_bucket_arn, "${var.state_bucket_arn}/*"]
  }

  statement {
    sid = "InfraManage"
    actions = [
      "ec2:*",
      "elasticloadbalancing:*",
      "ecs:*",
      "ecr:*",
      "rds:*",
      "logs:*",
      "budgets:*",
      "cloudwatch:*",
      "application-autoscaling:*",
      "secretsmanager:CreateSecret",
      "secretsmanager:DeleteSecret",
      "secretsmanager:DescribeSecret",
      "secretsmanager:PutSecretValue",
      "secretsmanager:TagResource",
      "secretsmanager:GetResourcePolicy",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arn_pattern]
  }

  # The destroy workflow asserts "no EKS in v0"; asserting absence still
  # requires the read. Deliberately read-only and separate from InfraManage.
  statement {
    sid       = "TeardownVerifyRead"
    actions   = ["eks:ListClusters"]
    resources = ["*"]
  }

  statement {
    sid = "IamManageScoped"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:PassRole",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:TagRole",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-ecs-execution",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-ecs-task",
    ]
  }

  statement {
    sid       = "OidcProviderRead"
    actions   = ["iam:GetOpenIDConnectProvider"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "${var.name_prefix}-github-deploy-policy"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}
