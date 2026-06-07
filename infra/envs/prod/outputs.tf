output "alb_url" {
  description = "Public HTTP URL of the ALB."
  value       = module.alb.alb_url
}

output "ecr_repository_url" {
  description = "ECR repository URL for the app image."
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS app service."
  value       = module.ecs.service_name
}

output "rds_endpoint" {
  description = "RDS connection endpoint (host:port)."
  value       = module.rds.db_endpoint
}

output "github_oidc_role_arn" {
  description = "ARN of the GitHub Actions deploy role."
  value       = module.iam_github_oidc.deploy_role_arn
}

output "db_secret_arn" {
  description = "ARN of the DB credentials secret. ARN only, never the value (ADR-0005)."
  value       = module.rds.db_secret_arn
}
