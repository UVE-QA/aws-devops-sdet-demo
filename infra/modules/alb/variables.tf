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
  description = "Port the app container listens on (target group port)."
  type        = number
  default     = 8000
}
