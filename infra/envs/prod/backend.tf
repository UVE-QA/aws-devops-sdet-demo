# S3 remote state for prod (ADR-0004). Same bucket as stage, different key.
# prod is a SCAFFOLD mirror of stage in v0 — not a full prod deployment.
# Phase 4 note: do NOT init this backend yet; validate with -backend=false.

terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "prod/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
