output "service_name" {
  description = "Name of the ECS service."
  value       = aws_ecs_service.this.name
}

output "task_definition_arn" {
  description = "ARN of the task definition (the api's is reused for one-off migrate/seed/db-assert via run-task)."
  value       = aws_ecs_task_definition.this.arn
}

output "security_group_id" {
  description = "Security group of the service's tasks (the api's is what the RDS SG allows 5432 from)."
  value       = aws_security_group.this.id
}

output "execution_role_arn" {
  description = "ARN of the task execution role (for iam:PassRole in the deploy policy)."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ARN of the task role (for iam:PassRole in the deploy policy)."
  value       = aws_iam_role.task.arn
}

output "container_name" {
  description = "Name of the container in the task definition (used by run-task overrides)."
  value       = var.service
}
