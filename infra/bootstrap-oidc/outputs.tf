output "github_oidc_role_arn" {
  description = "ARN of the GitHub Actions deploy role. Set as the OIDC_ROLE_ARN GitHub environment variable."
  value       = module.iam_github_oidc.deploy_role_arn
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC identity provider."
  value       = module.iam_github_oidc.oidc_provider_arn
}
