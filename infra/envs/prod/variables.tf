variable "region" {
  description = "AWS deployment region."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (used in tags and resource name prefix)."
  type        = string
  default     = "prod"
}

variable "owner" {
  description = "Value for the Owner tag on all resources."
  type        = string
}

variable "app_port" {
  description = "Port the app container listens on."
  type        = number
  default     = 8000
}

variable "app_image" {
  description = "Full ECR image reference for the app. Placeholder until an image is pushed."
  type        = string
  default     = "aws-devops-sdet-demo-app:bootstrap"
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of app tasks. Still 0: prod gets its own deploy role and promotion path in Phase 9.1, and until then nothing here should be able to raise billable tasks."
  type        = number
  default     = 0
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 14
}

variable "db_engine_version" {
  description = "PostgreSQL engine version (must match docker-compose major 16, ADR-0010)."
  type        = string
  default     = "16"
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "budget_enabled" {
  description = "Whether to create the monthly budget (teardown safety net)."
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

variable "budget_actual_threshold" {
  description = "Percentage of limit at which an ACTUAL-spend alert fires."
  type        = number
  default     = 50
}

variable "budget_forecast_threshold" {
  description = "Percentage of limit at which a FORECASTED-spend alert fires."
  type        = number
  default     = 100
}
