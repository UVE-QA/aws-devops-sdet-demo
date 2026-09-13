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

# THE CLUSTER, THEN ONE MODULE PER SERVICE (ADR-0095). `api` is what the one
# container used to be minus the page; `web` is the page. The api alone is
# handed the database secret and the api's security group alone is what RDS
# allows 5432 from - web has no business with either, and a role that could
# read the secret anyway would be the kind of thing this project draws.
module "ecs_cluster" {
  source = "../../modules/ecs-cluster"

  name_prefix = local.name_prefix
}

# The queue between the api and the worker (ADR-0096): one standard queue,
# its dead-letter queue and the alarm on it, per environment.
module "queue" {
  source = "../../modules/queue"

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
  # Where item.created goes (ADR-0096). A URL, not a secret.
  extra_environment = [{ name = "ITEMS_QUEUE_URL", value = module.queue.queue_url }]
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

# The worker (ADR-0096): the third service, behind no load balancer and on no
# port - a task that consumes the queue and writes the database. It holds the
# database secret, so its execution role gets the read below, and its task
# role gets the right to consume the one queue.
module "worker" {
  source = "../../modules/ecs-service"

  name_prefix       = local.name_prefix
  service           = "worker"
  app_env           = var.environment
  region            = var.region
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  cluster_id        = module.ecs_cluster.cluster_id
  image             = var.worker_image
  db_secret_arn     = module.rds.db_secret_arn
  log_group_name    = module.observability.log_group_name
  task_cpu          = var.task_cpu
  task_memory       = var.task_memory
  desired_count     = var.desired_count
  extra_environment = [{ name = "ITEMS_QUEUE_URL", value = module.queue.queue_url }]
  # The heartbeat the loop touches on every pass (worker/consumer/main.py):
  # a process that is up and stuck is what this tells apart from one that is
  # up and working.
  health_check_command = ["CMD-SHELL", "find /tmp/heartbeat -mmin -1 | grep -q . || exit 1"]
}

# THE ONE POLICY THAT MAY READ THE DATABASE SECRET, on the api's execution
# role and on nothing else (ADR-0095). Here rather than inside the service
# module: a policy counted into existence for one instance of a module and not
# the other is a resource the orphan-adoption gate cannot see, and a policy
# left on an orphaned role is exactly the DeleteConflict ADR-0041 was written
# about. Named for the api, findable by name.
data "aws_iam_policy_document" "api_read_db_secret" {
  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [module.rds.db_secret_arn]
  }
}

resource "aws_iam_role_policy" "api_read_db_secret" {
  name   = "${local.name_prefix}-api-read-db-secret"
  role   = module.api.execution_role_name
  policy = data.aws_iam_policy_document.api_read_db_secret.json
}

# THE WORKER READS THE SAME SECRET (ADR-0096): it writes the api's table, and
# until plan item 4 gives it data of its own that is the database it reaches.
# The same document, a second policy, on the worker's execution role and named
# for the worker - one policy per role, so the adoption gate can find each.
resource "aws_iam_role_policy" "worker_read_db_secret" {
  name   = "${local.name_prefix}-worker-read-db-secret"
  role   = module.worker.execution_role_name
  policy = data.aws_iam_policy_document.api_read_db_secret.json
}

# THE TASK ROLES' ONLY PERMISSIONS (ADR-0096): the api may put onto the one
# queue, the worker may take from it. Nothing on `*`, nothing either could do
# to the other's half - a task role that could delete messages from the api's
# side, or send them from the worker's, would be a permission nobody asked for
# drawn on the board as if somebody had.
data "aws_iam_policy_document" "api_publish_items" {
  statement {
    sid       = "PublishItems"
    actions   = ["sqs:SendMessage", "sqs:GetQueueUrl"]
    resources = [module.queue.queue_arn]
  }
}

resource "aws_iam_role_policy" "api_publish_items" {
  name   = "${local.name_prefix}-api-publish-items"
  role   = module.api.task_role_name
  policy = data.aws_iam_policy_document.api_publish_items.json
}

data "aws_iam_policy_document" "worker_consume_items" {
  statement {
    sid = "ConsumeItems"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [module.queue.queue_arn]
  }
}

resource "aws_iam_role_policy" "worker_consume_items" {
  name   = "${local.name_prefix}-worker-consume-items"
  role   = module.worker.task_role_name
  policy = data.aws_iam_policy_document.worker_consume_items.json
}

module "rds" {
  source = "../../modules/rds"

  name_prefix               = local.name_prefix
  vpc_id                    = module.network.vpc_id
  private_db_subnet_ids     = module.network.private_db_subnet_ids
  ecs_app_security_group_id = module.api.security_group_id
  # The worker reaches the database too (ADR-0096); still by group, never by CIDR.
  extra_client_security_group_ids = [module.worker.security_group_id]
  engine_version                  = var.db_engine_version
  instance_class                  = var.db_instance_class
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
