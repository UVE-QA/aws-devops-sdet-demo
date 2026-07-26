output "deploy_role_arn" {
  description = "ARN of the GitHub Actions deploy role for this environment. Set as the OIDC_ROLE_ARN variable on the matching GitHub Environment."
  value       = aws_iam_role.deploy.arn
}

output "deploy_role_name" {
  description = "Name of the deploy role, for workflows that build the ARN from an account id."
  value       = aws_iam_role.deploy.name
}
