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
