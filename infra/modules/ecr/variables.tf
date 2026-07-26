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

variable "untagged_expire_days" {
  description = "Days after which an untagged image is expired."
  type        = number
  default     = 1
}

variable "force_delete" {
  description = "Allow deleting a repository that still holds images. False by default: only a throwaway per-cycle repository should enable it (ADR-0018)."
  type        = bool
  default     = false
}
