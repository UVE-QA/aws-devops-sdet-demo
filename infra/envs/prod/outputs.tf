output "alb_url" {
  description = "Direct URL of the ALB. On prod this answers with a 301 to the public HTTPS name; it stays exported because run-task and debugging need a name that works before DNS has propagated."
  value       = module.alb.alb_url
}

output "app_url" {
  description = "The public URL of prod. This is what the smoke test targets and what the demo shows."
  value       = "https://${local.app_fqdn}"
}

output "app_fqdn" {
  description = "Public hostname of prod."
  value       = local.app_fqdn
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

output "db_secret_arn" {
  description = "ARN of the DB credentials secret. ARN only, never the value (ADR-0005)."
  value       = module.rds.db_secret_arn
}

output "task_definition_arn" {
  description = "ECS task definition ARN (reused for one-off migrate/seed/db-assert via run-task)."
  value       = module.ecs.task_definition_arn
}

output "ecs_app_security_group_id" {
  description = "Security group of the app/one-off tasks (run-task network config)."
  value       = module.ecs.app_security_group_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs where Fargate tasks run (run-task network config)."
  value       = module.network.public_subnet_ids
}

output "container_name" {
  description = "App container name for run-task containerOverrides."
  value       = module.ecs.container_name
}
