variable "log_group_name" {
  description = "Name of the CloudWatch log group for the app, e.g. /aws-devops-sdet-demo/stage/app."
  type        = string
}

variable "log_retention_days" {
  description = "Retention in days for the app log group. Short for stage to cap cost."
  type        = number
  default     = 7
}
