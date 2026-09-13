variable "name_prefix" {
  description = "Prefix for every name here, e.g. aws-devops-sdet-demo-lab."
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version of the control plane. One behind the newest EKS offers, so the controller and the addons have met it."
  type        = string
}

variable "vpc_id" {
  description = "The VPC the cluster lives in."
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for the control plane's ENIs and the nodes: the public ones, with public IPs (no NAT, ADR-0006)."
  type        = list(string)
}

variable "node_instance_types" {
  description = "Instance types of the managed node group."
  type        = list(string)
  default     = ["t3.small"]
}

variable "node_count" {
  description = "Desired nodes. Two, so a Deployment with two replicas has somewhere to go when one node is draining."
  type        = number
  default     = 2
}

variable "admin_principal_arns" {
  description = "IAM principals given cluster-admin by access entry, beside the creator: the owner's SSO role, so kubectl works from the devbox after a cycle created the cluster. The role's FULL ARN, path included: the first apply tried the path-stripped form the aws-auth ConfigMap wanted, and EKS answered `invalid principal`. NEVER the creator itself: the creator's entry is EKS's own, and a second one for the same principal is a 409 - so a local apply under the SSO role passes nothing here, and the workflow passes the SSO role."
  type        = list(string)
  default     = []
}

variable "queue_arn" {
  description = "ARN of the items queue the api publishes to and the worker consumes from (ADR-0096)."
  type        = string
}

variable "namespace" {
  description = "Namespace the application runs in; the IRSA trust policies name it."
  type        = string
  default     = "demo"
}

variable "api_service_account" {
  description = "Service account the api's pods run as."
  type        = string
  default     = "api"
}

variable "worker_service_account" {
  description = "Service account the worker's pods run as."
  type        = string
  default     = "worker"
}

variable "controller_service_account" {
  description = "Service account of the AWS Load Balancer Controller, in kube-system."
  type        = string
  default     = "aws-load-balancer-controller"
}
