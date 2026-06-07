output "deploy_role_arn" {
  description = "ARN of the GitHub Actions deploy role (set as GITHUB_OIDC_ROLE_ARN in the workflow)."
  value       = aws_iam_role.deploy.arn
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC identity provider."
  value       = aws_iam_openid_connect_provider.github.arn
}
