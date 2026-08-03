output "launch_url" {
  description = "The public endpoint the dashboard button posts to. GET issues a nonce, POST redeems it and launches. Goes into the page's SELF_SERVICE config in 19b."
  value       = aws_lambda_function_url.launch.function_url
}

output "control_table_name" {
  description = "The control store. Named in the launch workflow's release job, and the thing the break tests seed and then make unreadable."
  value       = aws_dynamodb_table.control.name
}

output "callback_role_arn" {
  description = "Role the launch workflow's release job assumes to delete the lock item. Goes into a GitHub variable; it is an identifier, not a credential."
  value       = aws_iam_role.callback.arn
}

output "budget_topic_arn" {
  description = "SNS topic the budget alarm publishes to, and the kill-switch Lambda listens on. Wire it into infra/envs/*/terraform.tfvars as budget_topic_arns in 19b."
  value       = aws_sns_topic.budget.arn
}

output "github_app_secret_name" {
  description = "Secrets Manager secret the GitHub App private key is pasted into BY HAND. Terraform creates the container and never holds the key (ADR-0034)."
  value       = aws_secretsmanager_secret.github_app_key.name
}

output "watchdog_function_name" {
  description = "The out-of-band watchdog. Invoke it directly to exercise the blunt path in 19c, with the AWS CLI as the witness."
  value       = aws_lambda_function.watchdog.function_name
}
