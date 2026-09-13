variable "name_prefix" {
  description = "Prefix for naming RDS resources, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the RDS SG lives."
  type        = string
}

variable "private_db_subnet_ids" {
  description = "Private DB subnet IDs for the RDS subnet group."
  type        = list(string)
}

variable "ecs_app_security_group_id" {
  description = "Security group ID of the api's tasks; RDS allows 5432 from this SG."
  type        = string
}

variable "extra_client_security_group_ids" {
  description = "Further security groups RDS allows 5432 from - the worker's, since ADR-0096. Still by group, never by CIDR."
  type        = list(string)
  default     = []
}

variable "engine_version" {
  description = "PostgreSQL engine version. Must match the docker-compose major version (16, ADR-0010)."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class (cost-conscious default)."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "demo"
}

variable "db_username" {
  description = "Master username."
  type        = string
  default     = "demo"
}
