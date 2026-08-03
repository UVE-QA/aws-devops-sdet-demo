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

variable "notification_topic_arns" {
  description = "SNS topics both notifications also publish to. Empty by default. The self-service level owns the topic and the Lambda that flips the kill switch when a message arrives (ADR-0035 guardrail 4); an email subscription cannot flip anything, and needs a confirmation click besides."
  type        = list(string)
  default     = []
}
