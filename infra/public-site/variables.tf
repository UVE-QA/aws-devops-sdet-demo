variable "region" {
  description = "AWS region for the site bucket and the publish role. The CloudFront certificate is NOT in this region; see the us_east_1 provider alias in main.tf."
  type        = string
  default     = "us-west-2"
}

variable "owner" {
  description = "Owner tag value for all resources."
  type        = string
}

variable "zone_name" {
  description = "The delegated subdomain this account owns. MUST equal var.zone_name in infra/dns and var.dns_zone_name in infra/envs/prod - a shared literal, like the project name, not an independent knob."
  type        = string
  default     = "demo.uveapp.net"
}

variable "site_bucket_name" {
  description = "Name of the private S3 bucket holding the dashboard. Globally unique, so it carries the account id. Deterministic on purpose: the publish workflow derives it without reading Terraform state."
  type        = string
}

variable "github_owner" {
  description = "GitHub org/owner allowed to assume the publish role."
  type        = string
  default     = "UVE-QA"
}

variable "github_repo" {
  description = "GitHub repository allowed to assume the publish role."
  type        = string
  default     = "aws-devops-sdet-demo"
}

variable "publish_environments" {
  description = "GitHub Environments whose workflows may assume the publish role. There is deliberately NO branch subject (ADR-0021 reasoning): every workflow that publishes already declares an environment, so a branch subject would only widen the trust for nothing."
  type        = list(string)
  default     = ["stage", "prod"]
}
