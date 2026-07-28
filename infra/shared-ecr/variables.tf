variable "region" {
  description = "AWS region for the shared registry."
  type        = string
  default     = "us-west-2"
}

variable "owner" {
  description = "Owner tag value for all resources."
  type        = string
}

variable "repository_name" {
  description = "Name of the shared ECR repository. Deterministic on purpose: workflows derive the image URL from it without reading Terraform state."
  type        = string
  default     = "aws-devops-sdet-demo-app"
}

variable "max_image_count" {
  description = "Tagged images to retain. Bounds storage cost on a level that is never destroyed. Raised from 10 to 30 in Phase 14: the rollback pointer names a digest that must still exist, and an ECR lifecycle rule can only expire, never protect a prefix (ADR-0029). The cap makes expiry of a last-good release unlikely; the check in promote-prod is what makes it safe."
  type        = number
  default     = 30
}
