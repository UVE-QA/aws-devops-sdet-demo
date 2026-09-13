output "cluster_name" {
  description = "Name of the cluster."
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "API server endpoint, for the kubernetes and helm providers."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_ca" {
  description = "Base64 CA of the API server, for the kubernetes and helm providers."
  value       = aws_eks_cluster.this.certificate_authority[0].data
}

output "cluster_version" {
  description = "Kubernetes version actually running."
  value       = aws_eks_cluster.this.version
}

output "cluster_security_group_id" {
  description = "The cluster security group, which the managed nodes carry: what RDS allows 5432 from in the lab."
  value       = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
}

output "node_group_name" {
  description = "Name of the managed node group."
  value       = aws_eks_node_group.this.node_group_name
}

output "oidc_provider_arn" {
  description = "ARN of the cluster's OIDC provider in IAM."
  value       = aws_iam_openid_connect_provider.this.arn
}

output "api_role_arn" {
  description = "IRSA role the api's service account assumes."
  value       = aws_iam_role.api.arn
}

output "worker_role_arn" {
  description = "IRSA role the worker's service account assumes."
  value       = aws_iam_role.worker.arn
}

output "controller_role_arn" {
  description = "IRSA role the AWS Load Balancer Controller assumes."
  value       = aws_iam_role.controller.arn
}

output "controller_service_account" {
  description = "Name of the controller's service account, for the Helm release."
  value       = var.controller_service_account
}

output "namespace" {
  description = "Namespace the application runs in."
  value       = var.namespace
}
