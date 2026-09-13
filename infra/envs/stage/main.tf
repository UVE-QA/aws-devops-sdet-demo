# Stage environment: wires all modules together. Module data flow is one-way:
# network -> alb -> ecs -> rds, plus ecr, observability, budgets.
# (GitHub OIDC provider + deploy role live in infra/bootstrap-oidc, separate state.)
# No terraform apply in Phase 4 (ADR-0014); validate only with -backend=false.

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

      # The TTL pair (ADR-0035). Both are EMPTY for an owner-run cycle and both
      # are set by the self-service launch workflow. They go to stage AND prod
      # in the same commit even though nothing public can reach prod: the last
      # time a shared fix was applied to one environment only, prod kept the
      # broken shape for seven weeks.
      ExpiresAt = var.expires_at
      Launch    = var.launch_id
    }
  }
}

locals {
  name_prefix = "aws-devops-sdet-demo-${var.environment}"
}

module "network" {
  source = "../../modules/network"

  name_prefix = local.name_prefix
}

module "observability" {
  source = "../../modules/observability"

  name_prefix        = local.name_prefix
  log_group_name     = "/aws-devops-sdet-demo/${var.environment}/app"
  log_retention_days = var.log_retention_days

  # The environment lives in the NAMESPACE, not in a dimension: a dimension
  # value is a billable custom metric of its own (ADR-0032).
  metric_namespace = "aws-devops-sdet-demo/${var.environment}"
}

module "alb" {
  source = "../../modules/alb"

  name_prefix       = local.name_prefix
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  app_port          = var.app_port
}

# THE CLUSTER, THEN ONE MODULE PER SERVICE (ADR-0095). `api` is what the one
# container used to be minus the page; `web` is the page. The api alone is
# handed the database secret and the api's security group alone is what RDS
# allows 5432 from - web has no business with either, and a role that could
# read the secret anyway would be the kind of thing this project draws.
module "ecs_cluster" {
  source = "../../modules/ecs-cluster"

  name_prefix = local.name_prefix
}

module "api" {
  source = "../../modules/ecs-service"

  name_prefix           = local.name_prefix
  service               = "api"
  app_env               = var.environment
  region                = var.region
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.target_group_arn
  cluster_id            = module.ecs_cluster.cluster_id
  image                 = var.api_image
  port                  = var.app_port
  db_secret_arn         = module.rds.db_secret_arn
  log_group_name        = module.observability.log_group_name
  task_cpu              = var.task_cpu
  task_memory           = var.task_memory
  desired_count         = var.desired_count
  # The image asks itself, the way it always has: python is what it carries.
  health_check_command = ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:${var.app_port}/health').status==200 else 1)\""]
  depends_on           = [module.alb]
}

module "web" {
  source = "../../modules/ecs-service"

  name_prefix           = local.name_prefix
  service               = "web"
  app_env               = var.environment
  region                = var.region
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.web_target_group_arn
  cluster_id            = module.ecs_cluster.cluster_id
  image                 = var.web_image
  port                  = var.web_port
  log_group_name        = module.observability.log_group_name
  task_cpu              = var.task_cpu
  task_memory           = var.task_memory
  desired_count         = var.desired_count
  # nginx:alpine carries wget and not python.
  health_check_command = ["CMD-SHELL", "wget -qO- http://127.0.0.1:${var.web_port}/healthz >/dev/null 2>&1 || exit 1"]
  depends_on           = [module.alb]
}

module "rds" {
  source = "../../modules/rds"

  name_prefix               = local.name_prefix
  vpc_id                    = module.network.vpc_id
  private_db_subnet_ids     = module.network.private_db_subnet_ids
  ecs_app_security_group_id = module.api.security_group_id
  engine_version            = var.db_engine_version
  instance_class            = var.db_instance_class
}


module "budgets" {
  source = "../../modules/budgets"

  name_prefix          = local.name_prefix
  enabled              = var.budget_enabled
  monthly_budget_limit = var.monthly_budget_limit
  budget_email         = var.budget_email
  actual_threshold     = var.budget_actual_threshold
  forecast_threshold   = var.budget_forecast_threshold

  # Where the kill switch listens (ADR-0035 guardrail 4). Empty until
  # infra/self-service is applied and its topic ARN is wired in.
  notification_topic_arns = var.budget_topic_arns
}
