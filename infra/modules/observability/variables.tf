variable "log_group_name" {
  description = "Name of the CloudWatch log group for the app, e.g. /aws-devops-sdet-demo/stage/app."
  type        = string
}

variable "log_retention_days" {
  description = "Retention in days for the app log group. Short for stage to cap cost."
  type        = number
  default     = 7
}

variable "name_prefix" {
  description = "Prefix for the metric filter and alarm names, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

# The environment is carried by the NAMESPACE rather than by a dimension: every
# distinct dimension value is a billable custom metric of its own, and stage and
# prod never share a namespace (ADR-0032).
variable "metric_namespace" {
  description = "CloudWatch namespace for the log-derived 5xx metric, e.g. aws-devops-sdet-demo/stage."
  type        = string
}

variable "metric_name" {
  description = "Name of the log-derived 5xx metric."
  type        = string
  default     = "AppHttp5xx"
}
