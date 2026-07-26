# S3 remote state for prod (ADR-0004). Same bucket as stage, different key, so
# the two environments can never write each other's state.
#
# This backend has never been initialized: prod is reconciled in Phase 9.0 and
# first applied in Phase 9.1. Validation runs with -backend=false and an
# isolated TF_DATA_DIR, so it needs no AWS credentials.

terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "prod/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
