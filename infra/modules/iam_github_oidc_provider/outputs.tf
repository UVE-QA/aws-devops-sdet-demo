output "arn" {
  description = "ARN of the GitHub OIDC identity provider; feed it to every iam_github_deploy_role instance."
  value       = aws_iam_openid_connect_provider.github.arn
}
