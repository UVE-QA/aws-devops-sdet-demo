# DNS level (permanent, ADR-0024): the hosted zone for the delegated subdomain
# and the ACM certificate the prod ALB terminates TLS with.
#
# WHY THIS IS NOT IN infra/envs/prod
#
# Two independent reasons, either one sufficient:
#
# 1. The zone's name servers are referenced by an NS record in the PARENT zone,
#    which lives in a different AWS account outside this Organization. Destroying
#    and recreating the zone assigns new name servers and silently breaks that
#    delegation - the demo would stop resolving and the fix would require access
#    to an account this project deliberately has no credentials for.
#
# 2. DNS validation of the certificate takes minutes. In an environment level it
#    would be re-validated on every cycle, adding both wall-clock time and a
#    failure mode to a path whose whole purpose is being repeatable.
#
# This is the same reasoning that moved the container registry out of the
# environments (ADR-0018): anything that must SURVIVE a teardown belongs above
# the environment levels.
#
# Applied LOCALLY (AWS_PROFILE=demo-admin), once per account. There is no
# destroy step for this level in the normal lifecycle.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project      = "aws-devops-sdet-demo"
      Environment  = "dns"
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
    }
  }
}

resource "aws_route53_zone" "demo" {
  name    = var.zone_name
  comment = "Delegated subdomain for aws-devops-sdet-demo. NS record in the parent zone is manual and lives in another account."

  tags = {
    Name = var.zone_name
  }
}

# Wildcard only. It covers app.<zone> today and anything else this account
# serves from the subdomain later.
#
# The apex <zone> is deliberately NOT a SAN here: the Phase 11 dashboard is
# served by CloudFront, which can only use a certificate issued in us-east-1.
# That certificate is a separate resource in a separate region, not an omission.
resource "aws_acm_certificate" "wildcard" {
  domain_name       = "*.${var.zone_name}"
  validation_method = "DNS"

  tags = {
    Name = "*.${var.zone_name}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "validation" {
  for_each = {
    for dvo in aws_acm_certificate.wildcard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id         = aws_route53_zone.demo.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

# Blocks the apply until the certificate is actually ISSUED. Without it the
# apply would succeed with a PENDING_VALIDATION certificate and the failure
# would surface later, in prod, as an unusable listener.
resource "aws_acm_certificate_validation" "wildcard" {
  certificate_arn         = aws_acm_certificate.wildcard.arn
  validation_record_fqdns = [for r in aws_route53_record.validation : r.fqdn]
}
