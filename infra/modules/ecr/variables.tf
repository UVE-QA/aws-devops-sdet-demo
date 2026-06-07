variable "repository_name" {
  description = "Name of the ECR repository for the app image."
  type        = string
  default     = "aws-devops-sdet-demo-app"
}

variable "max_image_count" {
  description = "Maximum number of images to retain; older images are expired by the lifecycle policy."
  type        = number
  default     = 10
}
