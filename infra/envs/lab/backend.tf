# The lab's state, in the same bucket as stage's and prod's and under its own
# key (ADR-0004, ADR-0097). Native S3 lockfile, no DynamoDB.
terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "lab/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
