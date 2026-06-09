terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-993912191738"
    key          = "bootstrap-oidc/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
