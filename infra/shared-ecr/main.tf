# Shared ECR (permanent level, ADR-0018). One repository, used by every
# environment, so an image built and tested in stage can be promoted to prod by
# DIGEST without being rebuilt.
#
# It lives here rather than in an environment because a workload environment is
# destroyed at the end of every cycle. A registry owned by infra/envs/stage
# would take prod's running image with it on the next stage teardown — prod
# would survive until its next pull and then fail with ImagePullFailure.
#
# Applied LOCALLY (AWS_PROFILE=demo-admin), once per ACCOUNT, not once per
# cycle. Same pattern as infra/bootstrap and infra/bootstrap-oidc. There is no
# destroy step for this level in the normal lifecycle.

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
      Environment  = "shared"
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
    }
  }
}

module "ecr" {
  source = "../modules/ecr"

  repository_name = var.repository_name
  max_image_count = var.max_image_count

  # A permanent level must not make image loss easy: force_delete exists for
  # per-cycle teardown idempotency (ADR-0011) and has no purpose here.
  force_delete = false
}

# ------------------------------------------------------------------------------
# Release pointer (ADR-0029): the digest of the last image whose prod smoke
# passed. It lives HERE, at a permanent level, for the same reason the registry
# does — a rollback target is worth exactly nothing if the teardown that created
# the need for it also deleted the target.
#
# The NAME is deterministic and duplicated in .github/workflows/promote-prod.yml
# and infra/bootstrap-oidc, deliberately, on the same reasoning as
# repository_name above: a workflow derives it without reading Terraform state.
# A variable that MUST equal a literal somewhere else is a drift surface, not a
# knob.
#
# THE "/release/" PREFIX IS LOAD-BEARING, not decoration. SSM refuses any
# parameter name beginning with "aws" or "ssm", case-insensitive, and this
# project is called aws-devops-sdet-demo — so the natural path
# /aws-devops-sdet-demo/... is rejected with AccessDeniedException "No access to
# reserved parameter name", which reads like a permissions problem and is not
# one. Do not tidy this segment away.
# ------------------------------------------------------------------------------
resource "aws_ssm_parameter" "prod_last_good_digest" {
  name        = "/release/aws-devops-sdet-demo/prod/last-good-image-digest"
  description = "Digest of the last image whose read-only smoke against prod passed. Written by promote-prod; read by its rollback step."
  type        = "String"
  tier        = "Standard" # free

  # Seed value only. "none" is the disarmed state and promote-prod refuses to
  # roll back to it out loud (ADR-0029 §5).
  value = "none"

  lifecycle {
    # WITHOUT THIS, every apply of this level resets the pointer to "none" and
    # silently disarms rollback until the next green promotion. The value is
    # owned by the workflow at run time; Terraform owns only the parameter's
    # existence.
    ignore_changes = [value]
  }
}
