output "cluster_name" {
  description = "Name of the lab cluster."
  value       = module.eks.cluster_name
}

output "cluster_version" {
  description = "Kubernetes version actually running."
  value       = module.eks.cluster_version
}

output "kubeconfig_command" {
  description = "How to point kubectl at the lab."
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "namespace" {
  description = "Namespace the chart installs into."
  value       = module.eks.namespace
}

output "api_role_arn" {
  description = "IRSA role for the api's service account; the chart annotates it."
  value       = module.eks.api_role_arn
}

output "worker_role_arn" {
  description = "IRSA role for the worker's service account; the chart annotates it."
  value       = module.eks.worker_role_arn
}

output "db_secret_name" {
  description = "Name of the Kubernetes Secret carrying DATABASE_URL; the chart mounts it."
  value       = kubernetes_secret_v1.db.metadata[0].name
}

output "items_queue_url" {
  description = "URL of the items queue; the chart passes it as ITEMS_QUEUE_URL."
  value       = module.queue.queue_url
}

output "items_queue_name" {
  description = "Name of the items queue, for the observation."
  value       = module.queue.queue_name
}

output "items_dead_letter_queue_name" {
  description = "Name of the dead-letter queue, for the observation."
  value       = module.queue.dead_letter_queue_name
}

output "items_dead_letter_alarm_name" {
  description = "Name of the alarm on the dead-letter queue, for the observation."
  value       = module.queue.dead_letter_alarm_name
}

output "vpc_id" {
  description = "The lab's VPC."
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "The lab's public subnets."
  value       = module.network.public_subnet_ids
}

output "db_secret_arn" {
  description = "ARN of the database credentials secret."
  value       = module.rds.db_secret_arn
}

output "results_queue_url" {
  description = "URL of the results queue (ADR-0098); the chart passes it as RESULTS_QUEUE_URL."
  value       = module.results.queue_url
}

output "results_queue_name" {
  description = "Name of the results queue, for the observation."
  value       = module.results.queue_name
}

output "results_dead_letter_queue_name" {
  description = "Name of the results dead-letter queue, for the observation."
  value       = module.results.dead_letter_queue_name
}
