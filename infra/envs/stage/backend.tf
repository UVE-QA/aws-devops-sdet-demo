# S3 remote state shared by local (demo-admin) and GitHub Actions (OIDC) runs
# (ADR-0004). The bucket is created by infra/bootstrap BEFORE this backend is
# initialized (ADR-0014). Native S3 lockfile, no DynamoDB.
#
# Phase 4 note: do NOT run `terraform init` against this backend yet. Validation
# in Phase 4 uses `terraform init -backend=false`. The real backend init happens
# in Phase 6 after the bootstrap apply.

terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "stage/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
