# The out-of-band watchdog, and the kill switch (ADR-0035 guardrails 3, 4, 5).
#
# WHY THIS IS NOT A CRON ON THE LIGHTSAIL DEVBOX
#
# The requirement is a failure domain separate from GitHub Actions: if Actions
# is the broken thing, the money still has to stop. `docs/next-phases.md` used
# to specify a devbox cron for that, and the mechanism does not survive this
# project's own rules. A cron has no human, the devbox reaches this account
# through IAM Identity Center with a device code somebody types, and an
# unattended path from that machine therefore means a static credential on disk.
#
# The domain actually distrusted is Actions, not AWS - and a watchdog
# independent of AWS could not act during an AWS outage anyway. EventBridge
# Scheduler plus a Lambda buys the same independence with no credential that
# outlives a request (ADR-0035 section 5).

resource "aws_cloudwatch_log_group" "watchdog" {
  name              = "/aws/lambda/${local.name_prefix}-watchdog"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "watchdog" {
  name               = "${local.name_prefix}-watchdog"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  tags = {
    Name = "${local.name_prefix}-watchdog"
  }
}

data "aws_iam_policy_document" "watchdog" {
  statement {
    sid = "ControlStore"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
    ]
    resources = [aws_dynamodb_table.control.arn]
  }

  statement {
    sid       = "GitHubAppKey"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.github_app_key.arn]
  }

  # Reads. None of these APIs supports resource-level permissions, so the
  # scoping that matters is on the DELETES below.
  statement {
    sid = "ObserveTheEnvironment"
    actions = [
      "ecs:ListClusters",
      "ecs:ListServices",
      "ecs:DescribeClusters",
      "ecs:DescribeServices",
      "ecs:ListTagsForResource",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeTags",
      "rds:DescribeDBInstances",
      "rds:ListTagsForResource",
    ]
    resources = ["*"]
  }

  # The blunt path. THIS is where two claims stop being statements about code
  # and become IAM. Every delete below is conditioned on THREE tags, and a
  # condition block here is an AND:
  #
  #   Project=aws-devops-sdet-demo   nothing else in the account
  #   Environment in var.watched_environments
  #                                  WAS `stage` alone, and that sentence -- "prod
  #                                  is unreachable, no bug in the handler and no
  #                                  value of any workflow input produces a call
  #                                  that deletes a prod resource" -- was true
  #                                  until ADR-0068. The public path now brings
  #                                  prod up, so the net has to cover what the
  #                                  path can create. A watchdog scoped to stage
  #                                  while the cycle deploys prod is not a
  #                                  narrower guarantee, it is an ABSENT one:
  #                                  a run that dies after the promotion leaves
  #                                  prod up with nothing able to remove it.
  #   Launch present and non-empty   the OWNER's own cycles are unreachable too.
  #                                  They carry Launch="", because guardrails are
  #                                  on the public path, not on the project. This
  #                                  is now the ONLY thing separating a public
  #                                  prod from the owner's, so it carries more
  #                                  weight than it did, and the Null test below
  #                                  is what stops an untagged resource from
  #                                  satisfying it by default.
  #
  # The Null test is not redundant with the StringNotEquals: for a resource with
  # NO Launch tag at all, a StringNotEquals condition evaluates TRUE, which is
  # the sort of quiet default that turns a policy into decoration.
  statement {
    # The name said InStageOnly until ADR-0068 widened the list under it, and a
    # policy statement whose Sid contradicts its own condition is worse than an
    # unnamed one: it is the sentence a reader checks INSTEAD of the condition.
    # Renamed in the same phase, not left for someone to trip over in the
    # console.
    sid = "BluntTeardownOfPublicLaunchesInWatchedEnvironments"
    actions = [
      "ecs:UpdateService",
      "ecs:DeleteService",
      "elasticloadbalancing:DeleteLoadBalancer",
      "rds:DeleteDBInstance",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["aws-devops-sdet-demo"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Environment"
      values   = var.watched_environments
    }

    condition {
      test     = "Null"
      variable = "aws:ResourceTag/Launch"
      values   = ["false"]
    }

    condition {
      test     = "StringNotEquals"
      variable = "aws:ResourceTag/Launch"
      values   = [""]
    }
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.watchdog.arn}:*"]
  }
}

resource "aws_iam_role_policy" "watchdog" {
  name   = "${local.name_prefix}-watchdog"
  role   = aws_iam_role.watchdog.id
  policy = data.aws_iam_policy_document.watchdog.json
}

resource "aws_lambda_function" "watchdog" {
  function_name = "${local.name_prefix}-watchdog"
  role          = aws_iam_role.watchdog.arn
  handler       = "watchdog_handler.handler"
  runtime       = "python3.12"
  timeout       = 120
  memory_size   = 256

  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256

  # One at a time. Two watchdogs observing the same environment would each see
  # the other's half-finished teardown and decide the blunt path was needed.
  # -1 while the account's concurrency quota is 10 - see the variable.
  reserved_concurrent_executions = var.internal_reserved_concurrency

  environment {
    variables = {
      CONTROL_TABLE      = aws_dynamodb_table.control.name
      GITHUB_OWNER       = var.github_owner
      GITHUB_REPO        = var.github_repo
      GITHUB_APP_ID      = var.github_app_id
      GITHUB_APP_SECRET  = aws_secretsmanager_secret.github_app_key.name
      GITHUB_INSTALL_ID  = var.github_app_installation_id
      DESTROY_WORKFLOW   = var.destroy_workflow_file
      STAGE_ENVIRONMENT  = var.stage_environment
      STAGE_NAME_PREFIX  = local.stage_prefix
      LOCK_GRACE_MINUTES = tostring(var.lock_grace_minutes)
    }
  }

  depends_on = [aws_cloudwatch_log_group.watchdog]

  tags = {
    Name = "${local.name_prefix}-watchdog"
  }
}

resource "aws_iam_role" "scheduler" {
  name = "${local.name_prefix}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "scheduler.amazonaws.com" }
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
      }
    }]
  })

  tags = {
    Name = "${local.name_prefix}-scheduler"
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${local.name_prefix}-scheduler"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.watchdog.arn
    }]
  })
}

resource "aws_scheduler_schedule" "watchdog" {
  name       = "${local.name_prefix}-watchdog"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "rate(${var.watchdog_interval_minutes} minutes)"
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_lambda_function.watchdog.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

# ---------------------------------------------------------------------------
# The kill switch (guardrail 4). A Lambda on the topic, because a flag has to be
# flipped by something, and an email cannot flip anything.
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "killswitch" {
  name              = "/aws/lambda/${local.name_prefix}-killswitch"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "killswitch" {
  name               = "${local.name_prefix}-killswitch"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  tags = {
    Name = "${local.name_prefix}-killswitch"
  }
}

data "aws_iam_policy_document" "killswitch" {
  statement {
    sid       = "FlipTheFlag"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.control.arn]

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "dynamodb:LeadingKeys"
      values   = ["killswitch"]
    }
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.killswitch.arn}:*"]
  }
}

resource "aws_iam_role_policy" "killswitch" {
  name   = "${local.name_prefix}-killswitch"
  role   = aws_iam_role.killswitch.id
  policy = data.aws_iam_policy_document.killswitch.json
}

resource "aws_lambda_function" "killswitch" {
  function_name = "${local.name_prefix}-killswitch"
  role          = aws_iam_role.killswitch.arn
  handler       = "killswitch_handler.handler"
  runtime       = "python3.12"
  timeout       = 20
  memory_size   = 128

  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256

  # A flag that is already set does not need a second writer.
  # -1 while the account's concurrency quota is 10 - see the variable.
  reserved_concurrent_executions = var.internal_reserved_concurrency

  environment {
    variables = {
      CONTROL_TABLE = aws_dynamodb_table.control.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.killswitch]

  tags = {
    Name = "${local.name_prefix}-killswitch"
  }
}

resource "aws_lambda_permission" "killswitch_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.killswitch.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.budget.arn
}

resource "aws_sns_topic_subscription" "killswitch" {
  topic_arn = aws_sns_topic.budget.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.killswitch.arn
}

# AWS Budgets publishes from a fixed service principal, and the budget lives in
# the SAME account here - so the policy is narrow rather than a wildcard.
data "aws_iam_policy_document" "budget_topic" {
  statement {
    sid     = "AllowBudgetsToPublish"
    actions = ["SNS:Publish"]
    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }
    resources = [aws_sns_topic.budget.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  # The owner, to fire break test 4 by hand: the message shape AWS Budgets
  # actually sends, with one field changed. The same technique as 16b's
  # injected log line, for the same reason - the shape has to be the real one,
  # or the test is about the fixture.
  statement {
    sid     = "AllowAccountAdminToPublish"
    actions = ["SNS:Publish"]
    principals {
      type        = "AWS"
      identifiers = [data.aws_caller_identity.current.account_id]
    }
    resources = [aws_sns_topic.budget.arn]
  }
}

resource "aws_sns_topic_policy" "budget" {
  arn    = aws_sns_topic.budget.arn
  policy = data.aws_iam_policy_document.budget_topic.json
}
