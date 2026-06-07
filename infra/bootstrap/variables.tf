variable "region" {
  description = "AWS region for the Terraform state bucket."
  type        = string
  default     = "us-west-2"
}

variable "state_bucket_name" {
  description = "Globally-unique name of the S3 bucket holding Terraform remote state. Convention: aws-devops-sdet-demo-tfstate-<demo_account_id>."
  type        = string
}

variable "owner" {
  description = "Value for the Owner tag on bootstrap resources."
  type        = string
}
