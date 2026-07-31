# Observability module: the CloudWatch log group for the app, managed by
# Terraform (NOT auto-created by ECS) so `terraform destroy` actually removes it
# instead of leaving it to accumulate logs across cycles (ADR-0011). Retention
# is short for stage to cap cost even if a group is somehow left behind.

resource "aws_cloudwatch_log_group" "app" {
  name              = var.log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name = var.log_group_name
  }
}

# The 5xx signal (ADR-0032). The filter reads the application's own JSON access
# line, so the alarm and the evidence are the same artifact: the line that
# raised it names the path, the request id and the duration. The ALB's
# HTTPCode_Target_5XX_Count is free and would need no log parsing, and knows
# none of those things.
#
# `$.status >= 500` is a NUMERIC comparison and only works because the app
# writes status as a JSON number. A quoted status compares as a string and this
# filter would match nothing, forever, while looking correct.
resource "aws_cloudwatch_log_metric_filter" "http_5xx" {
  name           = "${var.name_prefix}-http-5xx"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "{ $.status >= 500 }"

  metric_transformation {
    name      = var.metric_name
    namespace = var.metric_namespace
    value     = "1"

    # Without this the metric has no value to report for a period in which
    # nothing matched — which is fine for the alarm below, but makes the metric
    # unreadable on a graph. It does NOT cause a zero to be published when no
    # log line arrives at all; only when the log group is written to.
    default_value = 0
  }
}

# One alarm, on the metric above.
#
# treat_missing_data = "notBreaching" is not a preference. A metric filter that
# matches nothing publishes NOTHING - not a zero - so a healthy environment
# produces a metric with no data points and the default ("missing") leaves this
# alarm in INSUFFICIENT_DATA for its entire life. That state is
# indistinguishable, at a glance, from an alarm that was configured wrongly.
#
# No alarm_actions. An SNS email subscription must be confirmed by clicking a
# link, and this environment is destroyed every cycle: a topic beside it would
# ask for that click every cycle and notify nobody in between. The channel has
# to outlive what it reports on, which puts it at a permanent level - out of
# scope for this phase, and recorded in ADR-0032 rather than skipped quietly.
resource "aws_cloudwatch_metric_alarm" "http_5xx" {
  alarm_name        = "${var.name_prefix}-http-5xx"
  alarm_description = "Application returned a 5xx. Source: the app's JSON access log, not the ALB (ADR-0032)."

  namespace           = var.metric_namespace
  metric_name         = var.metric_name
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "${var.name_prefix}-http-5xx"
  }
}
