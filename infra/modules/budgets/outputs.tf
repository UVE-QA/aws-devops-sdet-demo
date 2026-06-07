output "budget_name" {
  description = "Name of the monthly cost budget, or null when disabled."
  value       = var.enabled ? aws_budgets_budget.monthly[0].name : null
}
