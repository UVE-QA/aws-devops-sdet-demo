variable "region" {
  description = "AWS region for the OIDC bootstrap level."
  type        = string
  default     = "us-west-2"
}

variable "owner" {
  description = "Owner tag value for all resources."
  type        = string
}

variable "state_bucket_name" {
  description = "Terraform state bucket name; each deploy role gets scoped S3 access to it."
  type        = string
}

variable "github_owner" {
  description = "GitHub org/owner allowed to assume the deploy roles."
  type        = string
  default     = "UVE-QA"
}

variable "github_repo" {
  description = "GitHub repository allowed to assume the deploy roles."
  type        = string
  default     = "aws-devops-sdet-demo"
}

variable "github_branch" {
  description = "Branch whose workflows may assume the STAGE deploy role directly. Prod has no branch subject on purpose (ADR-0021); its only path is the reviewer-gated GitHub Environment."
  type        = string
  default     = "main"
}
