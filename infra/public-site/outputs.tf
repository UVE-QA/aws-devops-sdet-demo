output "site_bucket_name" {
  description = "Private S3 bucket holding the dashboard. The publish workflow writes here; nothing reads it directly over the internet."
  value       = aws_s3_bucket.site.bucket
}

output "distribution_id" {
  description = "CloudFront distribution id. The publish workflow invalidates status.json against it after every write (ADR-0026)."
  value       = aws_cloudfront_distribution.site.id
}

output "distribution_domain_name" {
  description = "CloudFront's own domain name. Useful for verifying the distribution before DNS has propagated, and for checking it from a host whose resolver has cached something stale."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "site_url" {
  description = "The permanent public URL of the dashboard. Unlike app.<zone>, this one is up even when every environment is destroyed - which is the whole point."
  value       = "https://${local.site_domain}"
}

output "publish_role_arn" {
  description = "ARN of the narrow publish role the workflows assume to write the dashboard. Goes into a GitHub variable; it is an identifier, not a credential."
  value       = aws_iam_role.publish.arn
}

output "certificate_arn" {
  description = "ARN of the us-east-1 certificate CloudFront terminates TLS with. Distinct from the regional wildcard in infra/dns that the prod ALB uses."
  value       = aws_acm_certificate_validation.site.certificate_arn
}
