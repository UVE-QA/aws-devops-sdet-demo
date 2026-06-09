# Bootstrap (OIDC level): creates the GitHub OIDC provider and the Actions
# deploy role. Lives in its OWN remote state (key bootstrap-oidc/terraform.tfstate)
# so GitHub Actions never destroys the role it is authenticating with.
#
# Runs LOCALLY (AWS_PROFILE=demo-admin), once per cycle, BEFORE the first stage
# apply. This is by design (chicken-and-egg: Actions cannot assume a role that
# does not exist yet), the same pattern as infra/bootstrap for the state bucket.
# See docs/decisions/0015.

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

module "iam_github_oidc" {
  source = "../modules/iam_github_oidc"

  name_prefix      = var.name_prefix
  github_owner     = var.github_owner
  github_repo      = var.github_repo
  github_branch    = var.github_branch
  state_bucket_arn = "arn:aws:s3:::${var.state_bucket_name}"

  # Wildcard suffix: the DB secret carries a per-cycle random suffix
  # (recovery_window=0), so the deploy role must be scoped to the pattern,
  # not a fixed ARN that only exists after a stage apply.
  db_secret_arn_pattern = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.name_prefix}-db-credentials-*"
}
