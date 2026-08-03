# Self-service level (PERMANENT, ADR-0034): the one endpoint a stranger can
# press, and everything it uses to refuse.
#
# WHY THIS IS ITS OWN LEVEL, AND NOT PART OF infra/public-site
#
# Different blast radius - this is the only level that holds a long-lived GitHub
# credential - and a different lifecycle: a fresh account can have the dashboard
# without the button at all, and changing a rate limit must not re-apply the
# CloudFront distribution that serves the public face of the project.
#
# WHY IT IS PERMANENT
#
# The lock, the day counter and the kill switch are state ABOUT a cycle. A
# control that lives inside the environment it controls is destroyed by the
# thing it is controlling - the sixth arrival at the ADR-0027 rule, after the
# registry (ADR-0018), the hosted zone (ADR-0024), the dashboard (ADR-0027), the
# release pointer (ADR-0029) and the alarm's notification channel (ADR-0032).
#
# Applied LOCALLY (AWS_PROFILE=demo-admin), once per account, after
# infra/public-site. No workflow applies it and destroy.yml never names it.
#
# WHAT IS NOT HERE, AND MUST NOT BE
#
# The GitHub App's private key. Terraform creates the secret CONTAINER and the
# role that reads it; the key is pasted in by hand (ADR-0034). If a launch
# returns 401, check the App, its installation and the key before anything else.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project      = "aws-devops-sdet-demo"
      Environment  = "self-service"
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# The OIDC provider belongs to infra/bootstrap-oidc and is looked up by a fact
# about the world rather than through another level's remote state, exactly as
# infra/public-site does it. The lookup fails the plan outright if that level
# has not been applied, which is the intended ordering expressed as an error.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  name_prefix  = "aws-devops-sdet-demo-self-service"
  repo_ref     = "repo:${var.github_owner}/${var.github_repo}"
  stage_prefix = "aws-devops-sdet-demo-${var.stage_environment}"

  # The stage deploy role, by NAME. infra/bootstrap-oidc owns it; this level
  # only needs to be able to say "not prod" in a comment and mean it, and the
  # name is the identity both levels already agree on.
  stage_deploy_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.stage_prefix}-github-deploy"

  # One deployment package, three functions, three handlers. Built by
  # `make self-service-package`, which vendors PyJWT and cryptography - the
  # Lambda Python runtime ships neither, and minting a GitHub App installation
  # token means signing an RS256 JWT.
  package_dir = "${path.module}/build/package"
}

# ---------------------------------------------------------------------------
# The control store. One DynamoDB table, four kinds of item, all of them the
# answer to "may this launch happen".
#
#   lock                 the in-flight launch, with the run that holds it and
#                        the deadline that IS the TTL
#   count#<YYYY-MM-DD>   the day counter, incremented by a conditional write
#   killswitch           flipped by the budget alarm, read before anything else
#   nonce#<id>           single-use, expired by DynamoDB TTL
#
# PAY_PER_REQUEST because the traffic is a handful of items a day and a
# provisioned table would cost more than everything it protects.
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "control" {
  name         = "${local.name_prefix}-control"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  # Only the nonces carry `ttl`. DynamoDB deletes an item whose ttl has passed
  # and ignores every item that has none, which is why the lock's expiry is a
  # separate attribute the code reads: a lock must EXPIRE without vanishing, or
  # the watchdog loses the only record that a launch was ever in flight.
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${local.name_prefix}-control"
  }
}

# ---------------------------------------------------------------------------
# The one long-lived credential in the project (ADR-0034).
#
# Terraform creates the CONTAINER. The private key is pasted in by hand, and
# `ignore_changes` on the version keeps a later apply from reverting it or
# printing it. The claim this project makes is now:
#
#   no static AWS keys anywhere, and exactly one static GitHub credential,
#   held here, readable by one Lambda execution role and by nothing else.
# ---------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "github_app_key" {
  name        = "${local.name_prefix}/github-app-private-key"
  description = "PEM private key of the GitHub App that dispatches the launch workflow. Pasted by hand; Terraform never holds it."

  # A deleted secret name cannot be reused for 7 days by default, which turns a
  # taint-and-reapply of this level into a week's wait.
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-github-app-key"
  }
}

# ---------------------------------------------------------------------------
# Where the budget alarm arrives (ADR-0035 guardrail 4).
#
# A topic and a Lambda, not an email subscription: an email subscription needs a
# confirmation click, and a channel beside a per-cycle environment would ask for
# one every cycle. ADR-0032 reached the same sentence about the 5xx alarm.
#
# What it cannot do, said out loud: AWS Budgets evaluates a few times a day and
# lags by hours. It cannot stop the run that spent the money. It stops the NEXT
# one. The fast control is the TTL.
# ---------------------------------------------------------------------------
resource "aws_sns_topic" "budget" {
  name              = "${local.name_prefix}-budget"
  kms_master_key_id = "alias/aws/sns"

  tags = {
    Name = "${local.name_prefix}-budget"
  }
}

# The deployment package. `terraform validate` never evaluates a data source, so
# a missing build directory does not break `make tf-validate`; it breaks the
# plan, which is the moment it matters.
data "archive_file" "package" {
  type        = "zip"
  source_dir  = local.package_dir
  output_path = "${path.module}/build/package.zip"
}
