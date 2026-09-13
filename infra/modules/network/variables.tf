variable "name_prefix" {
  description = "Prefix for naming network resources, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the 2 public subnets (app/ALB)."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "CIDR blocks for the 2 private DB subnets (RDS)."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "public_subnet_extra_tags" {
  description = "Further tags on the public subnets. The lab sets kubernetes.io/role/elb = 1 so the AWS Load Balancer Controller can find them (ADR-0097); ECS environments set nothing."
  type        = map(string)
  default     = {}
}
