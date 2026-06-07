output "db_endpoint" {
  description = "RDS connection endpoint (host:port)."
  value       = aws_db_instance.this.endpoint
}

output "db_address" {
  description = "RDS host address."
  value       = aws_db_instance.this.address
}

output "db_secret_arn" {
  description = "ARN of the Secrets Manager secret holding DB credentials. ARN only, never the value (ADR-0005)."
  value       = aws_secretsmanager_secret.db.arn
}

output "rds_security_group_id" {
  description = "Security group ID of the RDS instance."
  value       = aws_security_group.rds.id
}
