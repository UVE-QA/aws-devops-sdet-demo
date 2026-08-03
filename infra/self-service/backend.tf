# S3 remote state for the self-service level (ADR-0004, ADR-0034). Same bucket
# as the other levels, own key. The bucket is created by infra/bootstrap first.
#
# This level is PERMANENT and is never referenced by destroy.yml. Everything the
# button uses to REFUSE - the in-flight lock, the day counter, the kill switch -
# is state about a cycle, and a control that lives inside the environment it
# controls is destroyed by the thing it is controlling (ADR-0027, sixth arrival).
terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "self-service/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
