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
