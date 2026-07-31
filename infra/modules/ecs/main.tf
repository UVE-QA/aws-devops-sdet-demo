# ECS module: Fargate cluster, app security group, IAM roles (execution + task),
# task definition, and service. The app runs in PUBLIC subnets with
# assign_public_ip = true (no NAT, ADR-0006); inbound is allowed only from the
# ALB SG. DB credentials are injected via the task definition `secrets` block
# (valueFrom = Secrets Manager ARN), never plaintext env (ADR-0005). The same
# task definition is reused for one-off migrate/seed/db-assert via run-task
# command overrides (ADR-0007) — see README.md.

resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = "${var.name_prefix}-cluster"
  }
}

resource "aws_security_group" "app" {
  name        = "${var.name_prefix}-app-sg"
  description = "ECS app SG: inbound only from ALB SG on the app port; all egress."
  vpc_id      = var.vpc_id

  ingress {
    description     = "App port from ALB SG only"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    description = "All outbound (ECR, Secrets Manager, CloudWatch, RDS via IGW)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-app-sg"
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

# Execution role: pull from ECR, write CloudWatch logs (AWS managed policy),
# plus read the specific DB secret.
resource "aws_iam_role" "execution" {
  name               = "${var.name_prefix}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json

  tags = {
    Name = "${var.name_prefix}-ecs-execution"
  }
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "read_db_secret" {
  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arn]
  }
}

resource "aws_iam_role_policy" "execution_read_secret" {
  name   = "${var.name_prefix}-read-db-secret"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.read_db_secret.json
}

# Task role: minimal for v0 (no AWS API calls from the app yet).
resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json

  tags = {
    Name = "${var.name_prefix}-ecs-task"
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.name_prefix}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = var.image
      essential = true
      portMappings = [
        {
          containerPort = var.app_port
          protocol      = "tcp"
        }
      ]
      # Non-secret configuration. APP_ENV tags every JSON log line with the
      # environment that produced it (ADR-0032), so a line lifted out of
      # CloudWatch cannot be mistaken for one from the other environment.
      environment = [
        {
          name  = "APP_ENV"
          value = var.app_env
        }
      ]
      # DB credentials come from Secrets Manager (valueFrom), not plaintext env.
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.db_secret_arn}:url::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "app"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:${var.app_port}/health').status==200 else 1)\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    }
  ])

  tags = {
    Name = "${var.name_prefix}-app"
  }
}

resource "aws_ecs_service" "app" {
  name            = "${var.name_prefix}-app"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = var.app_port
  }

  # Allow the one-off run-task overrides and ALB draining to settle.
  health_check_grace_period_seconds = 60

  tags = {
    Name = "${var.name_prefix}-app"
  }
}
