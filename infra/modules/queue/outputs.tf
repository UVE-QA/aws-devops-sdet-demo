output "queue_url" {
  description = "URL of the items queue - what the api publishes to and the worker consumes from."
  value       = aws_sqs_queue.items.id
}

output "queue_arn" {
  description = "ARN of the items queue, for the two task-role policies."
  value       = aws_sqs_queue.items.arn
}

output "queue_name" {
  description = "Name of the items queue, for the observation."
  value       = aws_sqs_queue.items.name
}

output "dead_letter_queue_url" {
  description = "URL of the dead-letter queue."
  value       = aws_sqs_queue.dead_letter.id
}

output "dead_letter_queue_name" {
  description = "Name of the dead-letter queue, for the observation."
  value       = aws_sqs_queue.dead_letter.name
}

output "dead_letter_alarm_name" {
  description = "Name of the alarm on the dead-letter queue; the observation reads its state."
  value       = aws_cloudwatch_metric_alarm.dead_letter_not_empty.alarm_name
}
