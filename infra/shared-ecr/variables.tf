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
  description = "Tagged images to retain. Bounds storage cost on a level that is never destroyed."
  type        = number
  default     = 10
}
