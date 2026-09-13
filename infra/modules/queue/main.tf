# One queue, its dead-letter queue, and the alarm that says the dead-letter
# queue is not empty (Phase 42, ADR-0096). Per environment, torn down with
# it. Instantiated twice since ADR-0098: `items`, the api's events to the
# worker, and `results`, the worker's reports back.
#
# STANDARD, NOT FIFO. At-least-once delivery is the contract the worker is
# written against - its one statement is idempotent by construction - and a
# FIFO queue would buy ordering nothing here needs at the price of a
# throughput ceiling and a suffix on the name.
#
# THE REDRIVE IS THE POINT. A message the worker cannot process is left, not
# deleted (worker/consumer/handler.py), and after `max_receive_count` receipts
# SQS moves it here. The alarm has NO action: there is nobody to page, and an
# action bound to nothing would be the appearance of one. Its state is what
# the environment observation reads and the page shows (ADR-0096 D4).
#
# The visibility timeout is 30 s here and 5 s in worker/local/elasticmq.conf,
# and that is the one deliberate difference between the two.

resource "aws_sqs_queue" "dead_letter" {
  name = "${var.name_prefix}-${var.name}-dlq"

  # Kept for the maximum so a poison message from early in a long cycle is
  # still there to look at when the cycle ends; the queue itself is destroyed
  # with the environment anyway.
  message_retention_seconds = 1209600

  # Encrypted at rest with the SQS-owned key: free, no KMS to manage or to
  # grant, and the checkov rule (CKV_AWS_27) is a rule this project agrees
  # with rather than one it skips.
  sqs_managed_sse_enabled = true

  tags = {
    Name = "${var.name_prefix}-${var.name}-dlq"
  }
}

resource "aws_sqs_queue" "items" {
  name = "${var.name_prefix}-${var.name}"

  visibility_timeout_seconds = var.visibility_timeout_seconds
  # Long polling by default, so a consumer that forgets to ask for it still
  # does not spin.
  receive_wait_time_seconds = 20

  sqs_managed_sse_enabled = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Name = "${var.name_prefix}-${var.name}"
  }
}

# The dead-letter queue is only ever a source, never a target of anything
# else; saying so keeps a later queue from pointing at it by mistake.
resource "aws_sqs_queue_redrive_allow_policy" "dead_letter" {
  queue_url = aws_sqs_queue.dead_letter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.items.arn]
  })
}

resource "aws_cloudwatch_metric_alarm" "dead_letter_not_empty" {
  alarm_name          = "${var.name_prefix}-${var.name}-dlq-not-empty"
  alarm_description   = "A message the worker could not process reached the dead-letter queue (ADR-0096)."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dead_letter.name
  }

  # No actions, on purpose - see the header.
  alarm_actions = []
  ok_actions    = []

  tags = {
    Name = "${var.name_prefix}-${var.name}-dlq-not-empty"
  }
}
