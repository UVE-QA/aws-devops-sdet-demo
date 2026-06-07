output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "IDs of the 2 public subnets (app/ALB)."
  value       = aws_subnet.public[*].id
}

output "private_db_subnet_ids" {
  description = "IDs of the 2 private DB subnets (RDS)."
  value       = aws_subnet.private_db[*].id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC."
  value       = aws_vpc.this.cidr_block
}
