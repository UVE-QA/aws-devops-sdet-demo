variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name. Fixed: this level IS the lab."
  type        = string
  default     = "lab"
}

variable "owner" {
  description = "Owner tag."
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version of the control plane (ADR-0097). One behind the newest EKS offers."
  type        = string
  default     = "1.35"
}

variable "node_instance_types" {
  description = "Instance types of the managed node group."
  type        = list(string)
  default     = ["t3.small"]
}

variable "node_count" {
  description = "Desired nodes."
  type        = number
  default     = 2
}

variable "admin_principal_arns" {
  description = "IAM principals given cluster-admin beside the creator - the owner's SSO role, its full ARN with the path. Passed as TF_VAR_admin_principal_arns for a local apply; a .tfvars here would stop the sizing reader (scripts/sizing.py)."
  type        = list(string)
  default     = []
}

variable "alb_controller_chart_version" {
  description = "Chart version of the AWS Load Balancer Controller; its IAM policy in modules/eks is from the same release."
  type        = string
  default     = "3.5.0"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version (ADR-0010)."
  type        = string
  default     = "16"
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "expires_at" {
  description = "The TTL tag (ADR-0035): when this environment is to be gone. Empty for an owner-run cycle."
  type        = string
  default     = ""
}

variable "launch_id" {
  description = "The launch tag (ADR-0035). Empty for an owner-run cycle."
  type        = string
  default     = ""
}
