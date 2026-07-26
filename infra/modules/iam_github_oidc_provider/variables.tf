variable "name_prefix" {
  description = "Prefix for the provider's Name tag, e.g. aws-devops-sdet-demo."
  type        = string
}

variable "thumbprint" {
  description = "GitHub OIDC root CA thumbprint. Modern AWS validates the endpoint against trusted CAs, so this is largely a formality, but verify it is current at first apply and update if GitHub rotates."
  type        = string
  default     = "6938fd4d98bab03faadb97b34396831e3780aea1"
}
