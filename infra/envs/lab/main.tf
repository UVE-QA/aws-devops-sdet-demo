# The lab (Phase 43, ADR-0097): the same three images by the same digests
# stage tested, on EKS instead of ECS - an environment of its own beside stage
# and prod, never instead of them. Its own VPC, database, secret and queue,
# exactly as the ECS environments have; where they have a cluster, services
# and a load balancer module, this has a cluster, a node group, and a Helm
# chart whose Ingress asks the AWS Load Balancer Controller for the balancer.
#
# TWO PROVIDERS THAT DO NOT EXIST UNTIL THE APPLY IS HALF DONE. The kubernetes
# and helm providers are configured from the cluster this configuration
# creates, which Terraform allows and every guide warns about: a plan that
# has to read Kubernetes before the cluster exists fails. Everything that
# touches Kubernetes here depends on `module.eks`, so the first apply creates
# the cluster before it asks it anything, and the destroy removes the Helm
# release before the cluster it runs on. Authentication is `aws eks get-token`
# on every call - the deploy role in CI, demo-admin locally - so no token is
# ever written into state.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.17"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project      = "aws-devops-sdet-demo"
      Environment  = var.environment
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
      ExpiresAt    = var.expires_at
      Launch       = var.launch_id
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_ca)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_ca)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
    }
  }
}

locals {
  name_prefix = "aws-devops-sdet-demo-${var.environment}"
}

module "network" {
  source = "../../modules/network"

  name_prefix = local.name_prefix
  # How the load balancer controller finds the subnets an Ingress may use.
  public_subnet_extra_tags = {
    "kubernetes.io/role/elb" = "1"
  }
}

# The queue between the api and the worker (ADR-0096), per environment.
module "queue" {
  source = "../../modules/queue"

  name_prefix = local.name_prefix
}

# The way back (ADR-0098): the worker's reports, consumed by the api.
module "results" {
  source = "../../modules/queue"

  name_prefix = local.name_prefix
  name        = "results"
}

module "eks" {
  source = "../../modules/eks"

  name_prefix          = local.name_prefix
  cluster_version      = var.cluster_version
  vpc_id               = module.network.vpc_id
  subnet_ids           = module.network.public_subnet_ids
  node_instance_types  = var.node_instance_types
  node_count           = var.node_count
  admin_principal_arns = var.admin_principal_arns
  queue_arn            = module.queue.queue_arn
  results_queue_arn    = module.results.queue_arn
}

# The database, reached from the nodes: the managed node group carries the
# cluster security group, so that is what RDS admits - every pod on every
# node, which is coarser than ECS's per-service group and is what Kubernetes
# offers short of network policies (not taken here).
module "rds" {
  source = "../../modules/rds"

  name_prefix               = local.name_prefix
  vpc_id                    = module.network.vpc_id
  private_db_subnet_ids     = module.network.private_db_subnet_ids
  ecs_app_security_group_id = module.eks.cluster_security_group_id
  engine_version            = var.db_engine_version
  instance_class            = var.db_instance_class
}
