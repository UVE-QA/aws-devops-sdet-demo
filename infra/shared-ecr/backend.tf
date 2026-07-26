# S3 remote state for the shared registry (ADR-0004, ADR-0018). Same bucket as
# the other levels, own key. The bucket is created by infra/bootstrap first.
terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "shared-ecr/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
