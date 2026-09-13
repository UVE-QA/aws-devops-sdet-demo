# The lab's cluster (Phase 43, ADR-0097): an EKS control plane, one managed
# node group, the cluster's OIDC provider for IRSA, and the IAM roles the
# application's service accounts assume. AWS only - the Kubernetes objects
# and the Helm releases live in the environment root (infra/envs/lab), where
# the kubernetes and helm providers are configured from this module's outputs.
#
# WHAT THIS IS BESIDE ECS. The same three images by the same digests, on a
# second runtime, in an environment of its own beside stage and prod - not
# instead of them, because replacing stage would lose the comparison. What
# ECS gave the task definition, Kubernetes gives the Deployment; what the task
# role was, the service account's IAM role is (IRSA); what the ALB module
# built, an Ingress asks the controller to build - and that last one is the
# teardown trap the plan named: a load balancer Terraform does not own.
#
# NODES, NOT FARGATE. EKS on Fargate is closer to this project's no-servers
# posture and further from the Kubernetes a reader expects: no DaemonSets, a
# CoreDNS patch, IP-mode targets only, slow pod starts. Two small on-demand
# nodes in the public subnets (no NAT, ADR-0006) are what the story needs.
#
# ACCESS ENTRIES, NOT aws-auth. Authentication mode API: the principal that
# creates the cluster is its first admin, and any further admin is an access
# entry a reader can list, not a line in a ConfigMap only kubectl can show.

data "aws_partition" "current" {}

locals {
  cluster_name = "${var.name_prefix}-eks"
}

# --- the control plane ------------------------------------------------------

data "aws_iam_policy_document" "cluster_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.name_prefix}-eks-cluster"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume.json

  tags = {
    Name = "${var.name_prefix}-eks-cluster"
  }
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "this" {
  name     = local.cluster_name
  version  = var.cluster_version
  role_arn = aws_iam_role.cluster.arn

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  # A control plane whose log group outlives it is a bill nobody reads;
  # nothing enabled, on purpose, until something needs it.
  enabled_cluster_log_types = []

  tags = {
    Name = local.cluster_name
  }

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

# Anyone besides the creator who may administer the cluster - the owner's
# SSO role, so kubectl works from the devbox after a cycle created it.
resource "aws_eks_access_entry" "admin" {
  for_each = toset(var.admin_principal_arns)

  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "admin" {
  for_each = toset(var.admin_principal_arns)

  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.admin]
}

# --- the nodes ----------------------------------------------------------------

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "${var.name_prefix}-eks-node"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json

  tags = {
    Name = "${var.name_prefix}-eks-node"
  }
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEKS_CNI_Policy",
    "AmazonEC2ContainerRegistryReadOnly",
  ])

  role       = aws_iam_role.node.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
}

resource "aws_eks_node_group" "this" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.name_prefix}-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.subnet_ids
  instance_types  = var.node_instance_types
  capacity_type   = "ON_DEMAND"
  ami_type        = "AL2023_x86_64_STANDARD"

  scaling_config {
    desired_size = var.node_count
    min_size     = 1
    max_size     = var.node_count + 1
  }

  update_config {
    max_unavailable = 1
  }

  tags = {
    Name = "${var.name_prefix}-nodes"
  }

  depends_on = [aws_iam_role_policy_attachment.node]
}

# --- the cluster's identity, for IRSA ---------------------------------------
#
# The cluster signs service-account tokens; registering its issuer as an OIDC
# provider is what lets an IAM role trust a service account by name. The task
# role's equivalent, and the reason the api and the worker get one role each
# below rather than the node's.

data "tls_certificate" "oidc" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "this" {
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.oidc.certificates[0].sha1_fingerprint]

  tags = {
    Name = local.cluster_name
  }
}

locals {
  oidc_host = replace(aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")
}
