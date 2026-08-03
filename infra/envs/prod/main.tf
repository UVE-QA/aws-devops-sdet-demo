# Prod environment: same module wiring as stage, differing only in name prefix,
# sizing and log retention. Reconciled in Phase 9.0 against the post-C2 modules.
#
# desired_count still defaults to 0: prod has no deploy role of its own yet
# (Phase 9.1 adds a second role in infra/bootstrap-oidc), so nothing should be
# able to raise billable tasks here by accident in the meantime.
#
# The GitHub OIDC provider and deploy roles live in infra/bootstrap-oidc
# (ADR-0015); the container registry lives in infra/shared-ecr (ADR-0018).
# Neither belongs in an environment that is destroyed every cycle.

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
  app_fqdn    = "app.${var.dns_zone_name}"
}

# The DNS level (infra/dns) is permanent and applied once per account. prod
# looks the zone and the certificate up BY NAME instead of reading that level's
# state, so the only thing the two levels share is a domain name.
#
# Both lookups fail the plan outright if infra/dns has not been applied. That is
# the intended ordering expressed as an error rather than as a comment nobody
# reads.
data "aws_route53_zone" "demo" {
  name         = "${var.dns_zone_name}."
  private_zone = false
}

data "aws_acm_certificate" "wildcard" {
  domain      = "*.${var.dns_zone_name}"
  statuses    = ["ISSUED"]
  most_recent = true
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

  # Present only in prod. stage passes nothing and stays on plain HTTP:80
  # (ADR-0017 D3) — the public HTTPS surface is a prod property, not a shared
  # invariant, so this is a deliberate difference rather than drift.
  certificate_arn = data.aws_acm_certificate.wildcard.arn
}

# The alias record is PER-CYCLE state and belongs here, not in infra/dns: the
# ALB it points at is created and destroyed with this environment, so the target
# changes every cycle. The zone survives a teardown; the record does not, and
# app.<zone> is a dead name while prod is down (ADR-0017 D2a).
resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.demo.zone_id
  name    = local.app_fqdn
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}

module "ecs" {
  source = "../../modules/ecs"

  name_prefix           = local.name_prefix
  app_env               = var.environment
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
  depends_on            = [module.alb]
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
