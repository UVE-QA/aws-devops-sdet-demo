output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = aws_ecs_cluster.this.arn
}

output "service_name" {
  description = "Name of the ECS app service."
  value       = aws_ecs_service.app.name
}

output "task_definition_arn" {
  description = "ARN of the app task definition (reused for one-off migrate/seed/db-assert via run-task)."
  value       = aws_ecs_task_definition.app.arn
}

output "app_security_group_id" {
  description = "Security group ID of the ECS app (referenced by the RDS SG to allow 5432)."
  value       = aws_security_group.app.id
}

output "execution_role_arn" {
  description = "ARN of the ECS task execution role (for iam:PassRole in the deploy policy)."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ARN of the ECS task role (for iam:PassRole in the deploy policy)."
  value       = aws_iam_role.task.arn
}
