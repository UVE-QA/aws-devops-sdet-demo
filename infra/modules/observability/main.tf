# Observability module: the CloudWatch log group for the app, managed by
# Terraform (NOT auto-created by ECS) so `terraform destroy` actually removes it
# instead of leaving it to accumulate logs across cycles (ADR-0011). Retention
# is short for stage to cap cost even if a group is somehow left behind.

resource "aws_cloudwatch_log_group" "app" {
  name              = var.log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name = var.log_group_name
  }
}
