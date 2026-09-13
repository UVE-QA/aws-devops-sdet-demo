variable "name_prefix" {
  description = "Prefix for every resource name, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "service" {
  description = "The service's short name - `api` or `web`. It names the resources, the container and the log stream prefix."
  type        = string
}

variable "region" {
  description = "AWS region, for the awslogs driver."
  type        = string
}

variable "vpc_id" {
  description = "VPC the service runs in."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnets the tasks run in (no NAT, ADR-0006)."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "The ALB's security group; the only source allowed onto the service's port. null for a service nothing connects to (the worker, ADR-0096): its group then has no ingress at all."
  type        = string
  default     = null
}

variable "target_group_arn" {
  description = "The target group the service registers in. null for a service behind no load balancer (the worker, ADR-0096)."
  type        = string
  default     = null
}

variable "extra_environment" {
  description = "Further non-secret environment for the container, as {name, value} pairs - the queue URL for the api and the worker (ADR-0096). Secrets never go here; that is what db_secret_arn is for."
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "cluster_id" {
  description = "The cluster the service runs in (modules/ecs-cluster)."
  type        = string
}

variable "image" {
  description = "Image reference for this service - a tag on stage, a digest on prod (ADR-0029)."
  type        = string
}

variable "port" {
  description = "The container port the service listens on and the ALB forwards to. null for a service that listens on nothing (the worker, ADR-0096)."
  type        = number
  default     = null

  validation {
    condition     = (var.port == null) == (var.target_group_arn == null) && (var.port == null) == (var.alb_security_group_id == null)
    error_message = "port, target_group_arn and alb_security_group_id are set together (a service behind the load balancer) or not at all (a service behind nothing)."
  }
}

variable "app_env" {
  description = "Environment name written into every log line (ADR-0032)."
  type        = string
}

variable "db_secret_arn" {
  description = "ARN of the database credentials secret, for the service that has a database to reach. null for one that does not: no secret is injected and no policy to read it is granted."
  type        = string
  default     = null
}

variable "log_group_name" {
  description = "CloudWatch log group the service writes to."
  type        = string
}

variable "health_check_command" {
  description = "The container-level health check, as a CMD-SHELL list. Each image knows how to ask itself."
  type        = list(string)
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
  description = "Number of tasks."
  type        = number
  default     = 1
}
