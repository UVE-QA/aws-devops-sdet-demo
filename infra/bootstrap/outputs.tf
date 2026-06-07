output "state_bucket_name" {
  description = "Name of the S3 bucket holding Terraform remote state. Use this in each environment's backend.tf."
  value       = aws_s3_bucket.tfstate.id
}

output "state_bucket_arn" {
  description = "ARN of the Terraform state bucket (for least-privilege IAM policies)."
  value       = aws_s3_bucket.tfstate.arn
}

output "state_bucket_region" {
  description = "Region of the Terraform state bucket."
  value       = var.region
}
