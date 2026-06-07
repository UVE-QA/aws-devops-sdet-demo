variable "name_prefix" {
  description = "Prefix for naming the budget, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "enabled" {
  description = "Whether to create the budget. Defaults true; stage keeps it on as a teardown safety net."
  type        = bool
  default     = true
}

variable "monthly_budget_limit" {
  description = "Monthly cost budget limit in USD."
  type        = string
  default     = "20"
}

variable "budget_email" {
  description = "Email address for budget alert notifications."
  type        = string
}

variable "actual_threshold" {
  description = "Percentage of the limit at which an ACTUAL-spend alert fires."
  type        = number
  default     = 50
}

variable "forecast_threshold" {
  description = "Percentage of the limit at which a FORECASTED-spend alert fires."
  type        = number
  default     = 100
}
