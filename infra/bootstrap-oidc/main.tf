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

  # Wildcard suffix: the DB secret carries a per-cycle random suffix
  # (recovery_window=0), so a deploy role must be scoped to the pattern, not a
  # fixed ARN that only exists after an apply.
  secret_arn_prefix = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret"
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
}

# ADR-0021 refactor: the provider and the stage role already exist in this
# state under the old combined module. These moves rename them in state instead
# of destroying and recreating them. At the next local apply the plan MUST show
# the prod role added and NOTHING destroyed; a destroy/recreate of the provider
# or the stage role means a move below is wrong — stop and fix it rather than
# applying, because recreating the provider invalidates the stage role's trust.
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
