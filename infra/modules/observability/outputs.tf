output "log_group_name" {
  description = "Name of the app CloudWatch log group (referenced by the ECS task definition logConfiguration)."
  value       = aws_cloudwatch_log_group.app.name
}

output "log_group_arn" {
  description = "ARN of the app CloudWatch log group (for least-privilege IAM policies)."
  value       = aws_cloudwatch_log_group.app.arn
}

output "http_5xx_alarm_name" {
  description = "Name of the 5xx alarm, so a teardown check and the break test can look it up by name."
  value       = aws_cloudwatch_metric_alarm.http_5xx.alarm_name
}

output "http_5xx_metric_namespace" {
  description = "Namespace of the log-derived 5xx metric."
  value       = var.metric_namespace
}
