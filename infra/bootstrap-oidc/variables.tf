variable "region" {
  description = "AWS region for the OIDC bootstrap level."
  type        = string
  default     = "us-west-2"
}

variable "owner" {
  description = "Owner tag value for all resources."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for OIDC/deploy-role naming. Must match the stage name_prefix so the scoped IAM/secret ARNs line up (e.g. aws-devops-sdet-demo-stage)."
  type        = string
  default     = "aws-devops-sdet-demo-stage"
}

variable "state_bucket_name" {
  description = "Terraform state bucket name; the deploy role gets scoped S3 access to it."
  type        = string
}

variable "github_owner" {
  description = "GitHub org/owner allowed to assume the deploy role."
  type        = string
  default     = "UVE-QA"
}

variable "github_repo" {
  description = "GitHub repository allowed to assume the deploy role."
  type        = string
  default     = "aws-devops-sdet-demo"
}

variable "github_branch" {
  description = "Branch whose workflows may assume the deploy role."
  type        = string
  default     = "main"
}
