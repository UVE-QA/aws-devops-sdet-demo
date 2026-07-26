output "zone_id" {
  description = "Route53 hosted zone ID for the delegated subdomain."
  value       = aws_route53_zone.demo.zone_id
}

output "zone_name" {
  description = "The delegated subdomain."
  value       = aws_route53_zone.demo.name
}

output "name_servers" {
  description = "Name servers for the delegated zone. These four values go into an NS record for this subdomain in the PARENT zone, which lives in another AWS account. That record is manual, one-time, and outside this state."
  value       = aws_route53_zone.demo.name_servers
}

output "certificate_arn" {
  description = "ARN of the issued wildcard certificate. prod looks it up by domain rather than reading this state, so the environments stay decoupled from this level's state layout."
  value       = aws_acm_certificate_validation.wildcard.certificate_arn
}
