output "alb_dns_name" {
  description = "DNS name of the ALB."
  value       = aws_lb.this.dns_name
}

output "alb_url" {
  description = "HTTP URL of the ALB (http://<dns_name>)."
  value       = "http://${aws_lb.this.dns_name}"
}

output "alb_security_group_id" {
  description = "Security group ID of the ALB (referenced by the ECS app SG to allow inbound)."
  value       = aws_security_group.alb.id
}

output "target_group_arn" {
  description = "ARN of the api's target group (the ECS api service registers in it)."
  value       = aws_lb_target_group.app.arn
}

output "web_target_group_arn" {
  description = "ARN of the web target group (the ECS web service registers in it), ADR-0095."
  value       = aws_lb_target_group.web.arn
}

output "listener_arn" {
  description = "ARN of the HTTP:80 listener."
  value       = aws_lb_listener.http.arn
}

output "alb_zone_id" {
  description = "Canonical hosted zone ID of the ALB, required by a Route53 alias record pointing at it."
  value       = aws_lb.this.zone_id
}

output "https_enabled" {
  description = "Whether this ALB terminates TLS. Lets an environment derive its own public URL scheme instead of hardcoding it twice."
  value       = local.https_enabled
}
