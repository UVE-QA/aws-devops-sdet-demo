output "repository_url" {
  description = "URL of the shared ECR repository (docker push/pull, ECS image reference)."
  value       = module.ecr.repository_url
}

output "repository_name" {
  description = "Name of the shared ECR repository."
  value       = module.ecr.repository_name
}

output "repository_arn" {
  description = "ARN of the shared ECR repository (for least-privilege IAM policies)."
  value       = module.ecr.repository_arn
}

output "prod_last_good_digest_parameter_name" {
  description = "Name of the SSM parameter holding the last-good prod image digest (ADR-0029)."
  value       = aws_ssm_parameter.prod_last_good_digest.name
}

output "prod_last_good_digest_parameter_arn" {
  description = "ARN of that parameter, for the prod deploy role's least-privilege statement."
  value       = aws_ssm_parameter.prod_last_good_digest.arn
}
