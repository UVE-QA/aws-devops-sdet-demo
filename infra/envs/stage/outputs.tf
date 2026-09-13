output "alb_url" {
  description = "Public HTTP URL of the ALB."
  value       = module.alb.alb_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.ecs_cluster.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS api service (what the waits and the one-off tasks address)."
  value       = module.api.service_name
}

output "ecs_web_service_name" {
  description = "Name of the ECS web service (ADR-0095); the deploy waits for it too."
  value       = module.web.service_name
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
  value       = module.api.task_definition_arn
}

output "ecs_app_security_group_id" {
  description = "Security group of the app/one-off tasks (run-task network config)."
  value       = module.api.security_group_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs where Fargate tasks run (run-task network config)."
  value       = module.network.public_subnet_ids
}

output "container_name" {
  description = "App container name for run-task containerOverrides."
  value       = module.api.container_name
}

output "ecs_worker_service_name" {
  description = "Name of the ECS worker service (ADR-0096); the deploy waits for it too."
  value       = module.worker.service_name
}

output "items_queue_url" {
  description = "URL of the items queue (ADR-0096)."
  value       = module.queue.queue_url
}

output "items_queue_name" {
  description = "Name of the items queue, for the observation."
  value       = module.queue.queue_name
}

output "items_dead_letter_queue_name" {
  description = "Name of the dead-letter queue, for the observation."
  value       = module.queue.dead_letter_queue_name
}

output "items_dead_letter_alarm_name" {
  description = "Name of the alarm on the dead-letter queue, for the observation."
  value       = module.queue.dead_letter_alarm_name
}

output "results_queue_name" {
  description = "Name of the results queue (ADR-0098), for the observation."
  value       = module.results.queue_name
}

output "results_dead_letter_queue_name" {
  description = "Name of the results dead-letter queue, for the observation."
  value       = module.results.dead_letter_queue_name
}

output "worker_task_definition_arn" {
  description = "ARN of the worker's task definition, for its one-off migration (ADR-0098 D6)."
  value       = module.worker.task_definition_arn
}

output "worker_container_name" {
  description = "Name of the worker's container, for run-task overrides."
  value       = module.worker.container_name
}

output "ecs_worker_security_group_id" {
  description = "The worker's security group, for its one-off migration task - the group RDS admits."
  value       = module.worker.security_group_id
}
