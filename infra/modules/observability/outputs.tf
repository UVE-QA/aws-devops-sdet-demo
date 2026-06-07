output "log_group_name" {
  description = "Name of the app CloudWatch log group (referenced by the ECS task definition logConfiguration)."
  value       = aws_cloudwatch_log_group.app.name
}

output "log_group_arn" {
  description = "ARN of the app CloudWatch log group (for least-privilege IAM policies)."
  value       = aws_cloudwatch_log_group.app.arn
}
