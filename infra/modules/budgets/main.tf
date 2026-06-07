# Budgets module: REQUIRED for this project (ADR-0011 safety net). Because the
# environment is brought up and torn down repeatedly, a forgotten teardown must
# trigger an alert. AWS Budgets itself is free. Two notifications: ACTUAL spend
# crossing actual_threshold, and FORECASTED spend crossing forecast_threshold.
# The budget can be disabled cleanly via enabled = false, but stage defaults on.

resource "aws_budgets_budget" "monthly" {
  count = var.enabled ? 1 : 0

  name         = "${var.name_prefix}-monthly"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.actual_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.forecast_threshold
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}
