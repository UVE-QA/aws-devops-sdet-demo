# ALB module: public Application Load Balancer, its security group, listeners,
# and a target group for the Fargate app. Target type is "ip" because Fargate
# tasks register by IP, not by instance. Health check path is /health
# (liveness, no DB — ADR-0008).
#
# HTTPS is OPTIONAL and off by default (certificate_arn = null), so an
# environment without a certificate keeps exactly the plain HTTP:80 behaviour it
# had before. With a certificate the module terminates TLS on 443 and turns
# :80 into a redirect. stage stays HTTP; prod is HTTPS (ADR-0017 D3).

locals {
  https_enabled = var.certificate_arn != null
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb-sg"
  description = "ALB SG: allow inbound HTTP:80 from the internet, all egress."
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Opened only when this ALB actually terminates TLS. A permanently open 443
  # with no listener behind it is a port that answers nothing while looking
  # reachable — the kind of thing that reads as configured and is not.
  dynamic "ingress" {
    for_each = local.https_enabled ? [1] : []
    content {
      description = "HTTPS from anywhere"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-alb-sg"
  }
}

resource "aws_lb" "this" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  # Malformed headers are dropped at the load balancer rather than forwarded to
  # the application. Free, and it removes a request-smuggling shape that the
  # app would otherwise have to be trusted to handle.
  drop_invalid_header_fields = true

  tags = {
    Name = "${var.name_prefix}-alb"
  }
}

resource "aws_lb_target_group" "app" {
  name        = "${var.name_prefix}-tg"
  port        = var.app_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.name_prefix}-tg"
  }
}

# Port 80 always exists. What it DOES depends on whether TLS is configured:
# it forwards when there is no certificate, and redirects when there is. Two
# dynamic blocks rather than two resources, so the listener is never destroyed
# and recreated when an environment gains a certificate.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = local.https_enabled ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.app.arn
    }
  }

  dynamic "default_action" {
    for_each = local.https_enabled ? [1] : []
    content {
      type = "redirect"

      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count = local.https_enabled ? 1 : 0

  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn

  # TLS 1.2 floor, TLS 1.3 preferred. The AWS default policy still permits
  # older suites; an HTTPS demo that ships a weak policy demonstrates the wrong
  # thing.
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
