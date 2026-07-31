variable "name_prefix" {
  description = "Prefix for naming ECS resources, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "region" {
  description = "AWS region (for the awslogs log driver)."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the app SG lives."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the Fargate service (assign_public_ip = true, no NAT)."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "ALB security group ID; the app SG allows inbound only from this SG."
  type        = string
}

variable "target_group_arn" {
  description = "ALB target group ARN the service registers into."
  type        = string
}

variable "image" {
  description = "Full ECR image reference (repo URL + tag) for the app container."
  type        = string
}

variable "app_port" {
  description = "Port the app container listens on."
  type        = number
  default     = 8000
}

variable "db_secret_arn" {
  description = "ARN of the Secrets Manager secret with DB credentials; read via task secrets valueFrom."
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name for the awslogs driver."
  type        = string
}

variable "task_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)."
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

variable "app_env" {
  description = "Value of APP_ENV inside the container: the environment name, e.g. stage or prod."
  type        = string
}
