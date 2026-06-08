# GitHub OIDC module: creates the OIDC identity provider and the deploy role
# that GitHub Actions assumes (no static keys, ADR-0003). The trust policy
# restricts to a specific owner/repo and branch. The deploy policy is
# least-privilege and demo-scoped. This module is created by the FIRST local
# apply (ADR-0014); Actions cannot assume a role that does not exist yet.

data "aws_caller_identity" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = {
    Name = "${var.name_prefix}-github-oidc"
  }
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = concat(
        ["repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/${var.github_branch}"],
        [for e in var.github_environments : "repo:${var.github_owner}/${var.github_repo}:environment:${e}"]
      )
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${var.name_prefix}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.trust.json

  tags = {
    Name = "${var.name_prefix}-github-deploy"
  }
}

# Least-privilege, demo-scoped deploy policy. Resource-level scoping is applied
# where it is cheap and meaningful (state bucket, DB secret, PassRole); the
# infrastructure-management actions (network/alb/ecs/rds/logs/budgets) use "*"
# because Terraform creates/destroys many short-lived resources whose ARNs are
# not known ahead of time in a repeatable cycle. This is a deliberate demo
# trade-off, documented in README.md.
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
    resources = [var.db_secret_arn]
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
      "iam:TagRole",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.name_prefix}-*",
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
