variable "region" {
  description = "AWS region for the certificate. Must be the region the ALB lives in: an ALB can only use a certificate issued in its own region."
  type        = string
  default     = "us-west-2"
}

variable "owner" {
  description = "Owner tag value for all resources."
  type        = string
}

variable "zone_name" {
  description = "The delegated subdomain this account owns. MUST equal var.dns_zone_name in infra/envs/prod - a shared literal, like the project name, not an independent knob."
  type        = string
  default     = "demo.uveapp.net"
}
