variable "name_prefix" {
  description = "Environment-scoped prefix, e.g. aws-devops-sdet-demo-stage. Determines the role name AND the ARNs this role is allowed to manage, so it is the boundary between environments."
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC identity provider (module iam_github_oidc_provider). This module does not create one: AWS allows only one per issuer URL per account."
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
  description = "Branch whose workflows may assume the role directly. Ignored when trust_branch_ref = false."
  type        = string
  default     = "main"
}

variable "trust_branch_ref" {
  description = "Whether a plain branch subject (ref:refs/heads/<branch>) may assume this role. MUST be false for any environment gated by required reviewers: a branch subject bypasses the GitHub Environment approval entirely."
  type        = bool
  default     = true
}

variable "github_environments" {
  description = "GitHub Actions environments allowed to assume the role (sub: environment:<name>). Covers jobs that declare environment:, e.g. destroy.yml and promote-prod.yml."
  type        = list(string)
  default     = []
}

variable "state_bucket_arn" {
  description = "ARN of the Terraform state bucket; the role gets scoped S3 access to it."
  type        = string
}

variable "db_secret_arn_pattern" {
  description = "ARN pattern (wildcard suffix) of the DB credentials secret; the role gets scoped GetSecretValue on it. Wildcard because the secret name carries a per-cycle random suffix (recovery_window=0)."
  type        = string
}
