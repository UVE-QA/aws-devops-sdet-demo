# The launch path: one Function URL, one Lambda, one dispatch.
#
# A Function URL rather than API Gateway (ADR-0034): one route, no authorizer to
# configure, no custom domain requirement. Reserved concurrency on the function
# bounds what an unauthenticated endpoint can cost by itself, independently of
# every guardrail in the code - the only control here that does not depend on
# the control store being readable.

resource "aws_cloudwatch_log_group" "launch" {
  name              = "/aws/lambda/${local.name_prefix}-launch"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "launch" {
  name               = "${local.name_prefix}-launch"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  tags = {
    Name = "${local.name_prefix}-launch"
  }
}

data "aws_iam_policy_document" "launch" {
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

  # The one long-lived credential, readable by this role and by the watchdog's,
  # and by nothing else. Naming the secret ARN rather than "*" is the whole
  # point of the sentence in ADR-0034.
  statement {
    sid       = "GitHubAppKey"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.github_app_key.arn]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.launch.arn}:*"]
  }
}

resource "aws_iam_role_policy" "launch" {
  name   = "${local.name_prefix}-launch"
  role   = aws_iam_role.launch.id
  policy = data.aws_iam_policy_document.launch.json
}

resource "aws_lambda_function" "launch" {
  function_name = "${local.name_prefix}-launch"
  role          = aws_iam_role.launch.arn
  handler       = "launch_handler.handler"
  runtime       = "python3.12"
  timeout       = 20
  memory_size   = 256

  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      CONTROL_TABLE     = aws_dynamodb_table.control.name
      GITHUB_OWNER      = var.github_owner
      GITHUB_REPO       = var.github_repo
      GITHUB_APP_ID     = var.github_app_id
      GITHUB_APP_SECRET = aws_secretsmanager_secret.github_app_key.name
      GITHUB_INSTALL_ID = var.github_app_installation_id
      WORKFLOW_FILE     = var.launch_workflow_file
      TTL_MINUTES       = tostring(var.ttl_minutes)
      DAILY_CAP         = tostring(var.daily_cap)
      NONCE_TTL_SECONDS = tostring(var.nonce_ttl_seconds)
      ALLOWED_ORIGIN    = var.allowed_origin
    }
  }

  depends_on = [aws_cloudwatch_log_group.launch]

  lifecycle {
    # An empty archive is what a forgotten build step looks like, and Lambda
    # accepts it happily. The number is a floor, not a size: the vendored
    # cryptography wheel alone is megabytes.
    precondition {
      condition     = data.archive_file.package.output_size > 500000
      error_message = "self-service: the deployment package is empty or unvendored. Run `make self-service-package` first - it vendors PyJWT and cryptography, which the Lambda runtime does not provide."
    }
  }

  tags = {
    Name = "${local.name_prefix}-launch"
  }
}

# AuthType NONE is the decision, not an oversight: the endpoint is public
# because the button is public. Nothing here authenticates the visitor and
# nothing pretends to (ADR-0034). What bounds the cost is ADR-0035, and the
# reserved concurrency above.
# Since October 2025 a NONE-auth function URL needs BOTH statements in the
# resource policy: lambda:InvokeFunctionUrl AND lambda:InvokeFunction. Missing
# the second one returns 403 Forbidden with no invocation and no log line -
# indistinguishable, from the outside, from a policy that is absent entirely.
#
# The provider creates the first statement itself when authorization_type is
# NONE; it does not create the second. That asymmetry is why this was found by
# applying rather than by reading: the configuration says NONE, the account
# says Forbidden, and nothing in between says why.
resource "aws_lambda_permission" "launch_url_invoke" {
  # checkov:skip=CKV_AWS_301: This function is publicly accessible BY DECISION (ADR-0034). What bounds it is ADR-0035 - the kill switch, the day counter, the lock and the TTL - not the absence of a public principal. Skipped INLINE rather than in .checkov.yaml so that any OTHER publicly accessible Lambda in this repository still fails the scan. Worth noting what the check could see: the InvokeFunctionUrl half is created by the provider and is invisible to Checkov, so this resource is the first thing that ever made the public grant scannable.
  statement_id             = "FunctionURLInvokeAllowPublicAccess"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.launch.function_name
  principal                = "*"
  invoked_via_function_url = true
}

resource "aws_lambda_function_url" "launch" {
  function_name      = aws_lambda_function.launch.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = [var.allowed_origin]
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
    max_age       = 300
  }
}

# ---------------------------------------------------------------------------
# The callback role: how the launch workflow RELEASES the lock.
#
# The lock is taken by the Lambda before the dispatch and released by the
# workflow's final job (ADR-0035 guardrail 1), which means that job needs a
# credential - and the stage deploy role is not it. This role can write exactly
# one item in one table and can do nothing else in the account.
#
# It is trusted on the `self-service` GitHub Environment rather than on a branch
# ref, for ADR-0021's reason: a branch subject would let any workflow on main
# assume it. GitHub creates that environment on the workflow's first run, with
# no protection rules - so unlike prod's gate, this needs no manual UI step.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "callback_trust" {
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
      values   = ["${local.repo_ref}:environment:self-service"]
    }
  }
}

resource "aws_iam_role" "callback" {
  name               = "${local.name_prefix}-callback"
  assume_role_policy = data.aws_iam_policy_document.callback_trust.json

  tags = {
    Name = "${local.name_prefix}-callback"
  }
}

data "aws_iam_policy_document" "callback" {
  statement {
    sid       = "ReleaseTheLock"
    actions   = ["dynamodb:GetItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.control.arn]

    # Only the lock item. A leading-key condition is the difference between "may
    # release the lock" and "may edit the day counter it is capped by".
    condition {
      test     = "ForAllValues:StringEquals"
      variable = "dynamodb:LeadingKeys"
      values   = ["lock"]
    }
  }
}

resource "aws_iam_role_policy" "callback" {
  name   = "${local.name_prefix}-callback"
  role   = aws_iam_role.callback.id
  policy = data.aws_iam_policy_document.callback.json
}
