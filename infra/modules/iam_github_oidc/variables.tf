variable "name_prefix" {
  description = "Prefix for naming OIDC resources, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "github_owner" {
  description = "GitHub org/owner allowed to assume the deploy role (e.g. UVE-QA)."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository allowed to assume the deploy role (e.g. aws-devops-sdet-demo)."
  type        = string
}

variable "github_branch" {
  description = "Branch whose workflows may assume the deploy role (e.g. main)."
  type        = string
  default     = "main"
}

variable "state_bucket_arn" {
  description = "ARN of the Terraform state bucket; the deploy role gets scoped S3 access to it."
  type        = string
}

variable "db_secret_arn" {
  description = "ARN of the DB credentials secret; the deploy role gets scoped GetSecretValue on it."
  type        = string
}

variable "github_environments" {
  description = "GitHub Actions environments allowed to assume the deploy role (sub: environment:<name>). Covers workflow_dispatch jobs that set environment:, e.g. destroy.yml."
  type        = list(string)
  default     = ["stage"]
}
