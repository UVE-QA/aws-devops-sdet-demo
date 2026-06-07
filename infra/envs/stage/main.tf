# Stage environment: wires all modules together. Module data flow is one-way:
# network -> alb -> ecs -> rds, plus ecr, observability, iam_github_oidc, budgets.
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

module "ecr" {
  source = "../../modules/ecr"

  repository_name = "aws-devops-sdet-demo-app"
}

module "observability" {
  source = "../../modules/observability"

  log_group_name     = "/aws-devops-sdet-demo/${var.environment}/app"
  log_retention_days = var.log_retention_days
}

module "alb" {
  source = "../../modules/alb"

  name_prefix       = local.name_prefix
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  app_port          = var.app_port
}

module "ecs" {
  source = "../../modules/ecs"

  name_prefix           = local.name_prefix
  region                = var.region
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.target_group_arn
  image                 = var.app_image
  app_port              = var.app_port
  db_secret_arn         = module.rds.db_secret_arn
  log_group_name        = module.observability.log_group_name
  task_cpu              = var.task_cpu
  task_memory           = var.task_memory
  desired_count         = var.desired_count
}

module "rds" {
  source = "../../modules/rds"

  name_prefix               = local.name_prefix
  vpc_id                    = module.network.vpc_id
  private_db_subnet_ids     = module.network.private_db_subnet_ids
  ecs_app_security_group_id = module.ecs.app_security_group_id
  engine_version            = var.db_engine_version
  instance_class            = var.db_instance_class
}

module "iam_github_oidc" {
  source = "../../modules/iam_github_oidc"

  name_prefix      = local.name_prefix
  github_owner     = var.github_owner
  github_repo      = var.github_repo
  github_branch    = var.github_branch
  state_bucket_arn = "arn:aws:s3:::${var.state_bucket_name}"
  db_secret_arn    = module.rds.db_secret_arn
}

module "budgets" {
  source = "../../modules/budgets"

  name_prefix          = local.name_prefix
  enabled              = var.budget_enabled
  monthly_budget_limit = var.monthly_budget_limit
  budget_email         = var.budget_email
  actual_threshold     = var.budget_actual_threshold
  forecast_threshold   = var.budget_forecast_threshold
}
