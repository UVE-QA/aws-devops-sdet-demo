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

variable "image_tag_mutability" {
  description = "MUTABLE or IMMUTABLE. Immutable by default (ADR-0029): a tag must keep naming the same digest, or \"the image stage tested\" stops being a fact. No exclusion is configured because nothing in this repository reads a floating tag."
  type        = string
  default     = "IMMUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability must be MUTABLE or IMMUTABLE."
  }
}
