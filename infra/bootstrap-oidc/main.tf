# Bootstrap (OIDC level): the GitHub OIDC identity provider and ONE deploy role
# PER ENVIRONMENT. Lives in its OWN remote state (key
# bootstrap-oidc/terraform.tfstate) so GitHub Actions never destroys the role it
# is authenticating with (ADR-0015).
#
# Runs LOCALLY (AWS_PROFILE=demo-admin), once per cycle, BEFORE the first stage
# apply. This is by design (chicken-and-egg: Actions cannot assume a role that
# does not exist yet), the same pattern as infra/bootstrap for the state bucket.
# See docs/decisions/0014 and 0015.
#
# The provider and the role are separate modules (ADR-0021): AWS allows exactly
# one OIDC provider per issuer URL per account, so the roles must be able to
# multiply without it.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project      = "aws-devops-sdet-demo"
      Environment  = "bootstrap-oidc"
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  # Must match locals.name_prefix in infra/envs/*/main.tf, which hardcodes the
  # same project literal. Kept as a literal here on purpose: a variable that
  # MUST equal a hardcoded value elsewhere is a drift surface, not a knob.
  project_name      = "aws-devops-sdet-demo"
  stage_name_prefix = "${local.project_name}-stage"
  prod_name_prefix  = "${local.project_name}-prod"
  lab_name_prefix   = "${local.project_name}-lab"

  # Wildcard suffix: the DB secret carries a per-cycle random suffix
  # (recovery_window=0), so a deploy role must be scoped to the pattern, not a
  # fixed ARN that only exists after an apply.
  secret_arn_prefix = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret"

  # Created by infra/shared-ecr (ADR-0029). The "release/" segment is required:
  # SSM reserves every parameter name starting with "aws", and the project name
  # does. See the comment on the resource itself.
  #
  # Referenced here as a constructed ARN
  # rather than via remote state: the name is deterministic on purpose, exactly
  # like repository_name, and a data-source dependency would order two permanent
  # levels against each other for no gain.
  prod_release_pointer_arn = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/release/${local.project_name}/prod/last-good-image-digest"
}

module "oidc_provider" {
  source = "../modules/iam_github_oidc_provider"

  name_prefix = local.project_name
}

module "deploy_role_stage" {
  source = "../modules/iam_github_deploy_role"

  name_prefix       = local.stage_name_prefix
  oidc_provider_arn = module.oidc_provider.arn

  github_owner = var.github_owner
  github_repo  = var.github_repo

  # Stage is not gated by reviewers: deploy-stage.yml runs on the branch, and
  # destroy.yml declares environment: stage.
  trust_branch_ref    = true
  github_branch       = var.github_branch
  github_environments = ["stage"]

  state_bucket_arn      = "arn:aws:s3:::${var.state_bucket_name}"
  db_secret_arn_pattern = "${local.secret_arn_prefix}:${local.stage_name_prefix}-db-credentials-*"
}

module "deploy_role_prod" {
  source = "../modules/iam_github_deploy_role"

  name_prefix       = local.prod_name_prefix
  oidc_provider_arn = module.oidc_provider.arn

  github_owner = var.github_owner
  github_repo  = var.github_repo

  # NO branch subject. The GitHub Environment "prod" carries required reviewers,
  # and a ref:refs/heads/main subject would let any workflow on main assume this
  # role without ever reaching the approval gate. This single false is the
  # approval gate's teeth on the AWS side.
  trust_branch_ref    = false
  github_environments = ["prod"]

  state_bucket_arn      = "arn:aws:s3:::${var.state_bucket_name}"
  db_secret_arn_pattern = "${local.secret_arn_prefix}:${local.prod_name_prefix}-db-credentials-*"

  # Only prod rolls back, so only prod's role can read or write the pointer.
  release_pointer_parameter_arns = [local.prod_release_pointer_arn]
}

# The lab's role (ADR-0097): stage's trust shape - the branch and the GitHub
# Environment `lab` - plus the cluster, its OIDC provider and its five roles.
# Same repository, same OIDC provider, its own name prefix, so it grants
# nothing over stage or prod.
module "deploy_role_lab" {
  source = "../modules/iam_github_deploy_role"

  name_prefix       = local.lab_name_prefix
  oidc_provider_arn = module.oidc_provider.arn

  github_owner = var.github_owner
  github_repo  = var.github_repo

  trust_branch_ref    = true
  github_branch       = var.github_branch
  github_environments = ["lab"]

  state_bucket_arn      = "arn:aws:s3:::${var.state_bucket_name}"
  db_secret_arn_pattern = "${local.secret_arn_prefix}:${local.lab_name_prefix}-db-credentials-*"

  eks                      = true
  extra_managed_role_names = ["eks-cluster", "eks-node", "api-irsa", "worker-irsa", "alb-controller"]
}

# ADR-0021 refactor: the provider and the stage role already exist in this
# state under the old combined module. These moves rename them in state instead
# of destroying and recreating them. At the next local apply the plan MUST show
# the prod role added and NOTHING destroyed; a destroy/recreate of the provider
# or the stage role means a move below is wrong — stop and fix it rather than
# applying, because recreating the provider invalidates the stage role's trust.
# CI'S ONE RIGHT: PULL THE BASE IMAGES AS THIS ACCOUNT (2026-09-30). ci.yml
# builds the three images to test and to scan them, and it pulled python and
# nginx from ECR Public anonymously - a limit per IP address, on runners whose
# addresses are everyone's. On 2026-09-30 `image-scan` on `main` met
# `429 Too Many Requests - Data limit exceeded` on eight tries over two runs.
# The cycle's deploy roles got the same two token reads the same day; this
# role is those two reads and nothing else - no state, no registry of ours, no
# environment. Trusted by pushes to `main` and `next` and by pull requests of
# this repository only; not by an environment, because CI deploys nothing.
data "aws_iam_policy_document" "ci_pull_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [module.oidc_provider.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/next",
        "repo:${var.github_owner}/${var.github_repo}:pull_request",
      ]
    }
  }
}

resource "aws_iam_role" "ci_pull" {
  name               = "${local.project_name}-ci-pull"
  description        = "ci.yml only: sign in to ECR Public to pull the base images. Nothing else."
  assume_role_policy = data.aws_iam_policy_document.ci_pull_trust.json
}

data "aws_iam_policy_document" "ci_pull" {
  statement {
    sid = "PublicRegistryPull"
    actions = [
      "ecr-public:GetAuthorizationToken",
      "sts:GetServiceBearerToken",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "ci_pull" {
  name   = "${local.project_name}-ci-pull"
  role   = aws_iam_role.ci_pull.id
  policy = data.aws_iam_policy_document.ci_pull.json
}

moved {
  from = module.iam_github_oidc.aws_iam_openid_connect_provider.github
  to   = module.oidc_provider.aws_iam_openid_connect_provider.github
}

moved {
  from = module.iam_github_oidc.aws_iam_role.deploy
  to   = module.deploy_role_stage.aws_iam_role.deploy
}

moved {
  from = module.iam_github_oidc.aws_iam_role_policy.deploy
  to   = module.deploy_role_stage.aws_iam_role_policy.deploy
}
