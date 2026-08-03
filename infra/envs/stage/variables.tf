variable "region" {
  description = "AWS deployment region."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (used in tags and resource name prefix)."
  type        = string
  default     = "stage"
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
  description = "Full ECR image reference for the app. Placeholder until the first image is pushed in Phase 6."
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
  description = "Number of app tasks to run."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days (short for stage)."
  type        = number
  default     = 7
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

variable "expires_at" {
  description = "RFC3339 deadline after which this environment may be destroyed by the out-of-band watchdog (ADR-0035 guardrail 3). Empty for an owner-run cycle, which is deliberate: an empty deadline plus an empty launch_id is what says 'a human is watching this one'. Set by the self-service launch workflow, never by hand."
  type        = string
  default     = ""
}

variable "launch_id" {
  description = "Id of the public launch that created this environment, or empty for an owner-run cycle. It is the tag the watchdog and its IAM policy both key off: a resource with an EMPTY launch_id cannot be deleted by the watchdog at all, which is what keeps a guardrail for strangers from tearing down a cycle the owner is in the middle of."
  type        = string
  default     = ""
}

variable "budget_topic_arns" {
  description = "SNS topics the budget notifications also publish to. `terraform output budget_topic_arn` from infra/self-service. Empty by default: the budget must keep working in an account that has never had the button (ADR-0035)."
  type        = list(string)
  default     = []
}
