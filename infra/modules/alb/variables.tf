variable "name_prefix" {
  description = "Prefix for naming ALB resources, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the ALB and target group live."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the internet-facing ALB."
  type        = list(string)
}

variable "app_port" {
  description = "Port the api container listens on (its target group's port)."
  type        = number
  default     = 8000
}

variable "web_port" {
  description = "Port the web container listens on (its target group's port), ADR-0095."
  type        = number
  default     = 80
}

variable "certificate_arn" {
  description = "ACM certificate for TLS termination, issued in THIS region (an ALB cannot use a certificate from another region). null means plain HTTP on :80 — the pre-HTTPS behaviour, which stage keeps."
  type        = string
  default     = null
}
