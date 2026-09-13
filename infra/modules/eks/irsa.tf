# The roles the application's service accounts assume (IRSA), one per service
# and one for the platform: what the task role was on ECS (ADR-0096 D6), here.
# Each trusts exactly one service account in exactly one namespace, and holds
# exactly the permission that service needs - the api may put onto the queue,
# the worker may take from it, the load balancer controller may build what an
# Ingress asks for. Nothing on `*` for the application; the controller's
# policy is the one its project publishes, vendored beside this file.

data "aws_iam_policy_document" "irsa_trust" {
  for_each = {
    api        = { namespace = var.namespace, service_account = var.api_service_account }
    worker     = { namespace = var.namespace, service_account = var.worker_service_account }
    controller = { namespace = "kube-system", service_account = var.controller_service_account }
  }

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.this.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = ["system:serviceaccount:${each.value.namespace}:${each.value.service_account}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

# --- the api: publish ---------------------------------------------------------

resource "aws_iam_role" "api" {
  name               = "${var.name_prefix}-api-irsa"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust["api"].json

  tags = {
    Name = "${var.name_prefix}-api-irsa"
  }
}

data "aws_iam_policy_document" "api_publish_items" {
  statement {
    sid       = "PublishItems"
    actions   = ["sqs:SendMessage", "sqs:GetQueueUrl"]
    resources = [var.queue_arn]
  }
  # The way back (ADR-0098): the api takes the worker's reports.
  statement {
    sid = "ConsumeResults"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [var.results_queue_arn]
  }
}

resource "aws_iam_role_policy" "api_publish_items" {
  name   = "${var.name_prefix}-api-publish-items"
  role   = aws_iam_role.api.name
  policy = data.aws_iam_policy_document.api_publish_items.json
}

# --- the worker: consume ------------------------------------------------------

resource "aws_iam_role" "worker" {
  name               = "${var.name_prefix}-worker-irsa"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust["worker"].json

  tags = {
    Name = "${var.name_prefix}-worker-irsa"
  }
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
    resources = [var.queue_arn]
  }
  # The way back (ADR-0098): the worker puts its reports.
  statement {
    sid       = "PublishResults"
    actions   = ["sqs:SendMessage", "sqs:GetQueueUrl"]
    resources = [var.results_queue_arn]
  }
}

resource "aws_iam_role_policy" "worker_consume_items" {
  name   = "${var.name_prefix}-worker-consume-items"
  role   = aws_iam_role.worker.name
  policy = data.aws_iam_policy_document.worker_consume_items.json
}

# --- the platform: the AWS Load Balancer Controller -------------------------
#
# The policy is the controller project's own, vendored as
# alb-controller-policy.json from the release the chart installs (v3.5.0);
# the version is in the environment root beside the chart's, so the two are
# bumped together. It is wide by nature - the controller creates balancers,
# target groups, listeners, security groups - and it is the one wide policy
# in this module, held by the one service account that needs it.

resource "aws_iam_role" "controller" {
  name               = "${var.name_prefix}-alb-controller"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust["controller"].json

  tags = {
    Name = "${var.name_prefix}-alb-controller"
  }
}

resource "aws_iam_role_policy" "controller" {
  name   = "${var.name_prefix}-alb-controller"
  role   = aws_iam_role.controller.name
  policy = file("${path.module}/alb-controller-policy.json")
}
