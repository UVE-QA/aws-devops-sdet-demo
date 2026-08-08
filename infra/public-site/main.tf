# Public site level (permanent, ADR-0027): the dashboard that stays online when
# every workload environment is destroyed.
#
# WHY THIS IS NOT IN infra/envs/*
#
# The dashboard exists to show, honestly, that both environments are gone. A
# dashboard inside an environment would be deleted by the very teardown it is
# there to report. Same reasoning as the container registry (ADR-0018) and the
# hosted zone (ADR-0024): anything that must SURVIVE a teardown belongs above
# the environment levels, and that includes the evidence that the teardown
# happened.
#
# Applied LOCALLY (AWS_PROFILE=demo-admin), once per account. There is no
# destroy step for this level in the normal lifecycle. Removing it by hand takes
# two passes, because a CloudFront distribution must be disabled before it can
# be deleted.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  name_prefix = "aws-devops-sdet-demo-site"
  site_domain = var.zone_name
  www_domain  = "www.${var.zone_name}"
  repo_ref    = "repo:${var.github_owner}/${var.github_repo}"

  publish_subjects = [for e in var.publish_environments : "${local.repo_ref}:environment:${e}"]
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project      = "aws-devops-sdet-demo"
      Environment  = "public-site"
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
    }
  }
}

# CloudFront can only use a certificate issued in us-east-1. The prod ALB can
# only use one issued in its own region. Two certificates, two regions, one
# domain - not duplication to be tidied away later (ADR-0027).
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project      = "aws-devops-sdet-demo"
      Environment  = "public-site"
      ManagedBy    = "terraform"
      Owner        = var.owner
      AccountModel = "aws-organizations-member-account"
    }
  }
}

# The zone belongs to infra/dns and the OIDC provider to infra/bootstrap-oidc.
# Both are looked up by a fact about the world - a domain name, an issuer URL -
# rather than through another level's remote state, so the levels stay coupled
# by identity instead of by state layout. Both lookups fail the plan outright if
# the level that owns them has not been applied, which is the intended ordering
# expressed as an error rather than as a comment nobody reads.
data "aws_route53_zone" "demo" {
  name         = "${var.zone_name}."
  private_zone = false
}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# ---------------------------------------------------------------------------
# Bucket: private, reachable only through CloudFront's Origin Access Control.
# A public bucket would serve the same files and is the pattern every security
# review flags; the private-bucket-with-OAC shape is itself an exhibit.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "site" {
  bucket = var.site_bucket_name

  tags = {
    Name = var.site_bucket_name
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# The dashboard HTML is rebuilt from git, but status/, reports/ and timeline/
# are NOT: they are written by the lifecycle workflows and exist nowhere else.
# Phase 11.1b already added a guard to stop the site sync deleting them, and
# 20b.1 added the third prefix to it; versioning is the half that survives the
# guard being wrong.
resource "aws_s3_bucket_versioning" "site" {
  bucket = aws_s3_bucket.site.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "site" {
  bucket = aws_s3_bucket.site.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ---------------------------------------------------------------------------
# Certificate, in us-east-1 because CloudFront accepts nothing else.
# The apex is here and NOT in the infra/dns wildcard: a wildcard does not cover
# the apex, and that certificate is regional anyway.
# ---------------------------------------------------------------------------

resource "aws_acm_certificate" "site" {
  provider = aws.us_east_1

  domain_name               = local.site_domain
  subject_alternative_names = [local.www_domain]
  validation_method         = "DNS"

  tags = {
    Name = local.site_domain
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.site.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id         = data.aws_route53_zone.demo.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

# Blocks the apply until the certificate is ISSUED. Without it the apply would
# succeed with a PENDING_VALIDATION certificate and the failure would surface
# later, in CloudFront, as a distribution that cannot serve the alias.
resource "aws_acm_certificate_validation" "site" {
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.site.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

# ---------------------------------------------------------------------------
# CloudFront
# ---------------------------------------------------------------------------

data "aws_cloudfront_response_headers_policy" "security_headers" {
  name = "Managed-SecurityHeadersPolicy"
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${local.name_prefix}-oac"
  description                       = "Origin Access Control for the public dashboard bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Public dashboard for aws-devops-sdet-demo"
  default_root_object = "index.html"
  aliases             = [local.site_domain, local.www_domain]

  # North America and Europe only. This is a portfolio page, not a product.
  price_class = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # AWS managed policy "CachingOptimized". status.json is invalidated by the
    # publish step (ADR-0026), so caching it aggressively is safe; without that
    # invalidation the page would report a destroyed environment as still up.
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"

    # HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy and a
    # default CSP, from the AWS managed policy. Resolved BY NAME rather than by
    # the GUID above: a wrong name fails at plan time with something readable,
    # where a wrong GUID fails at apply with an id nobody can look up.
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security_headers.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.site.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name = "${local.name_prefix}-distribution"
  }
}

data "aws_iam_policy_document" "site_bucket" {
  statement {
    sid       = "AllowCloudFrontRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    # Without this condition the policy would let ANY CloudFront distribution in
    # ANY account read the bucket. It is the whole point of OAC.
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site_bucket.json
}

# ---------------------------------------------------------------------------
# DNS: the dashboard is always up, app.<zone> is on demand and points elsewhere.
# ---------------------------------------------------------------------------

resource "aws_route53_record" "site_a" {
  for_each = toset([local.site_domain, local.www_domain])

  zone_id = data.aws_route53_zone.demo.zone_id
  name    = each.value
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "site_aaaa" {
  for_each = toset([local.site_domain, local.www_domain])

  zone_id = data.aws_route53_zone.demo.zone_id
  name    = each.value
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

# ---------------------------------------------------------------------------
# Publish role (ADR-0026): the workflows write status.json and the Playwright
# report here. Narrow by construction - this bucket, this distribution, nothing
# else. It is NOT the deploy role: a role that can change infrastructure has no
# business writing the page that reports on it.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "publish_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.publish_subjects
    }
  }
}

resource "aws_iam_role" "publish" {
  name               = "${local.name_prefix}-publish"
  assume_role_policy = data.aws_iam_policy_document.publish_trust.json

  tags = {
    Name = "${local.name_prefix}-publish"
  }

  lifecycle {
    # An empty subject list produces a trust policy nothing can satisfy, which
    # fails at the next OIDC login with an opaque STS error rather than here.
    precondition {
      condition     = length(local.publish_subjects) > 0
      error_message = "public-site: publish_environments is empty, so the publish role would trust nothing."
    }
  }
}

data "aws_iam_policy_document" "publish" {
  statement {
    sid       = "WriteSiteObjects"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]
  }

  statement {
    sid       = "ListSiteBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.site.arn]
  }

  statement {
    sid       = "InvalidateDistribution"
    actions   = ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"]
    resources = [aws_cloudfront_distribution.site.arn]
  }
}

resource "aws_iam_role_policy" "publish" {
  name   = "${local.name_prefix}-publish"
  role   = aws_iam_role.publish.id
  policy = data.aws_iam_policy_document.publish.json
}
