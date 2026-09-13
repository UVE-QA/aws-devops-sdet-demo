# One Fargate service (ADR-0095): its security group, its two IAM roles, its
# task definition and the service itself. Instantiated once per service - `api`,
# `web` and, since ADR-0096, `worker` - in the cluster modules/ecs-cluster
# makes. The service runs in PUBLIC subnets with assign_public_ip = true (no
# NAT, ADR-0006); inbound is allowed only from the ALB's security group, on
# this service's port - and a service with no port (the worker) gets a group
# with no ingress at all and no load balancer, which is what "nothing connects
# to it" looks like as configuration.
#
# WHAT IS PER SERVICE ON PURPOSE. Only a service that is given the database
# secret has it injected into its task, and only its execution role is granted
# the read - by a policy the environment attaches, see below: `web` serves
# static files and has no business holding a credential to the database, and a
# role that could read it anyway is the kind of thing this project draws on its
# board. The security group is per service for the same reason - the RDS module
# allows 5432 from the groups of the services that reach it and from nothing
# else. The task role is where a service's own AWS permissions go - the api's
# right to publish to the queue, the worker's to consume from it - and those
# too are policies the environment attaches, named for the service.
#
# DB credentials are injected via the task definition `secrets` block (valueFrom
# = Secrets Manager ARN), never plaintext env (ADR-0005). The api's task
# definition is reused for one-off migrate/seed/db-assert via run-task command
# overrides (ADR-0007).

locals {
  name = "${var.name_prefix}-${var.service}"
  # A service without a secret gets no policy and no `secrets` block at all,
  # rather than an empty one: absence is the statement.
  has_secret = var.db_secret_arn != null && var.db_secret_arn != ""
  # A service behind the load balancer has a port, a target group and an
  # ingress rule; one behind nothing has none of the three (variables.tf
  # refuses the half-way states).
  exposed = var.port != null
}

resource "aws_security_group" "this" {
  name        = "${local.name}-sg"
  description = local.exposed ? "ECS ${var.service} SG: inbound only from ALB SG on port ${var.port}; all egress." : "ECS ${var.service} SG: no inbound; all egress."
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = local.exposed ? [1] : []
    content {
      description     = "Service port from ALB SG only"
      from_port       = var.port
      to_port         = var.port
      protocol        = "tcp"
      security_groups = [var.alb_security_group_id]
    }
  }

  egress {
    description = "All outbound (ECR, Secrets Manager, CloudWatch, RDS via IGW)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-sg"
  }
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Execution role: pull from ECR, write CloudWatch logs (AWS managed policy).
# The api's also reads the database secret, through a policy the environment
# attaches to it - see above.
resource "aws_iam_role" "execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json

  tags = {
    Name = "${local.name}-ecs-execution"
  }
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# THE POLICY THAT READS THE SECRET IS NOT IN THIS MODULE. It is attached at
# the environment level, to the api's execution role alone (ADR-0095): a
# `count`ed policy inside a module called twice is a resource that exists in
# one instance and not the other, and the orphan-adoption gate reads modules
# and cannot tell which. A plain resource in the environment, named for the
# api, is a thing every reader of infra/ can find.

# Task role: minimal (no AWS API calls from either service).
resource "aws_iam_role" "task" {
  name               = "${local.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json

  tags = {
    Name = "${local.name}-ecs-task"
  }
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = var.service
      image     = var.image
      essential = true
      portMappings = local.exposed ? [
        {
          containerPort = var.port
          protocol      = "tcp"
        }
      ] : []
      # Non-secret configuration. APP_ENV tags every JSON log line with the
      # environment that produced it (ADR-0032), so a line lifted out of
      # CloudWatch cannot be mistaken for one from the other environment.
      environment = concat([
        {
          name  = "APP_ENV"
          value = var.app_env
        }
      ], var.extra_environment)
      # DB credentials come from Secrets Manager (valueFrom), not plaintext env;
      # and only for the service that has a database to reach.
      secrets = local.has_secret ? [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.db_secret_arn}:url::"
        }
      ] : []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = var.service
        }
      }
      healthCheck = {
        command     = var.health_check_command
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    }
  ])

  tags = {
    Name = local.name
  }
}

resource "aws_ecs_service" "this" {
  name            = local.name
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.this.id]
    assign_public_ip = true
  }

  dynamic "load_balancer" {
    for_each = local.exposed ? [1] : []
    content {
      target_group_arn = var.target_group_arn
      container_name   = var.service
      container_port   = var.port
    }
  }

  # Allow the one-off run-task overrides and ALB draining to settle. Only
  # meaningful - and only accepted - with a load balancer.
  health_check_grace_period_seconds = local.exposed ? 60 : null

  tags = {
    Name = local.name
  }
}
