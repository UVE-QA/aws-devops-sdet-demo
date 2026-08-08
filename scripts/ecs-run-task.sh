#!/usr/bin/env bash
# Run one command as a one-off ECS Fargate task and fail on a non-zero exit.
#
# Extracted from deploy-stage.yml and promote-prod.yml, which each carried
# their own copy of this loop. Two copies of a helper are two places to fix a
# bug in, and this project has already paid for that once: the ecs/alb ordering
# fix went to stage and prod kept the broken shape for seven weeks. The
# environment-override support below is exactly the kind of change that would
# otherwise have landed in one copy only.
#
# Reads the target from the environment:
#   CLUSTER TASK_DEF CONTAINER SUBNETS SG
#
# Usage:
#   scripts/ecs-run-task.sh <label> <command-json> [<environment-json>]
#
#   scripts/ecs-run-task.sh migrate '["alembic","upgrade","head"]'
#   scripts/ecs-run-task.sh ui-assert '["python","scripts/assert_ui_write.py"]' \
#       '[{"name":"UI_PROBE_NAME","value":"ui-probe-123"}]'
set -euo pipefail

label="${1:?usage: ecs-run-task.sh <label> <command-json> [<environment-json>]}"
command_json="${2:?missing command JSON}"
environment_json="${3:-[]}"

: "${CLUSTER:?CLUSTER is not set}"
: "${TASK_DEF:?TASK_DEF is not set}"
: "${CONTAINER:?CONTAINER is not set}"
: "${SUBNETS:?SUBNETS is not set}"
: "${SG:?SG is not set}"

overrides="$(jq -nc \
  --arg name "$CONTAINER" \
  --argjson cmd "$command_json" \
  --argjson env "$environment_json" \
  '{containerOverrides:[{name:$name, command:$cmd, environment:$env}]}')"

echo "::group::run-task $label"
arn="$(aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$TASK_DEF" \
  --launch-type FARGATE \
  --count 1 \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=ENABLED}" \
  --overrides "$overrides" \
  --query 'tasks[0].taskArn' --output text)"
echo "task: $arn"

aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$arn"

code="$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$arn" \
  --query 'tasks[0].containers[0].exitCode' --output text)"
echo "exitCode: $code"
echo "::endgroup::"

# ---- what the task actually SAID -------------------------------------------
#
# Until Phase 20c this script observed an exit code and nothing else. A db
# assertion that failed in AWS printed `exitCode: 1` and never which check
# failed - the answer was in CloudWatch, and nobody was looking. Since ADR-0042
# the map reads those lines too, so they are fetched here, once, for both
# readers.
#
# The log group and stream prefix come from the TASK DEFINITION rather than from
# a variable this script would have to be told: the definition is what actually
# configured the driver, and a second copy of that name is a second thing to
# keep in step. The stream is <prefix>/<container>/<task id>, which is the awslogs
# driver's own layout.
#
# Nothing here can fail the task. A log that cannot be fetched is reported as
# exactly that; it is not silence dressed as success, and the fold downstream
# refuses on a log with no PASS/FAIL line rather than calling it a pass.
task_id="${arn##*/}"
log_options="$(aws ecs describe-task-definition --task-definition "$TASK_DEF" \
  --query "taskDefinition.containerDefinitions[?name=='${CONTAINER}'].logConfiguration.options | [0]" \
  --output json 2>/dev/null || echo '{}')"
log_group="$(printf '%s' "$log_options" | jq -r '."awslogs-group" // empty')"
log_prefix="$(printf '%s' "$log_options" | jq -r '."awslogs-stream-prefix" // empty')"

if [ -n "$log_group" ] && [ -n "$log_prefix" ]; then
  stream="${log_prefix}/${CONTAINER}/${task_id}"
  # ONE EVENT PER LINE. `--output text` on an ARRAY joins its elements with
  # TABS, so every message the task printed arrives as a single line - and the
  # cycle of 2026-08-08 is what taught this file so. The db assertion passed both
  # its checks, the capture held both, and the map published
  # `db: incomplete, 1 passed, 1 not_run`, because the fold anchors a verdict to
  # the start of a line and there was only ever one line.
  #
  # The first explanation reached for was a race - the task stops, the last line
  # has not been delivered - and a stability wait was written for it before the
  # log was read. The log refuted it in one command. The wait below is KEPT as a
  # precaution, because a stopped task genuinely may have undelivered lines, but
  # it has never been seen to fire and it fixed nothing here. What fixed it is
  # the line above this comment: json out, jq per message.
  events=""
  prev_count=-1
  stable=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    events="$(aws logs get-log-events \
      --log-group-name "$log_group" --log-stream-name "$stream" \
      --start-from-head --output json 2>/dev/null | jq -r '.events[].message' || true)"
    count="$(printf '%s' "$events" | grep -c . || true)"
    if [ "$count" -gt 0 ] && [ "$count" -eq "$prev_count" ]; then
      stable=1
      break
    fi
    prev_count="$count"
    sleep 3
  done
  if [ -n "$events" ] && [ "$stable" != "1" ]; then
    echo "::warning::log for $label never stopped growing (last count: ${prev_count}); what follows may be partial"
  fi
  if [ -n "$events" ]; then
    echo "::group::log $label"
    printf '%s\n' "$events"
    echo "::endgroup::"
    if [ -n "${TASK_LOG_DIR:-}" ]; then
      mkdir -p "$TASK_LOG_DIR"
      printf '%s\n' "$events" > "${TASK_LOG_DIR}/${label}.log"
      echo "log written: ${TASK_LOG_DIR}/${label}.log"
    fi
  else
    echo "no log events for $label at ${log_group}:${stream} after 15s"
  fi
else
  echo "no awslogs configuration on ${TASK_DEF} for container ${CONTAINER}; no log to fetch"
fi

if [ "$code" != "0" ]; then
  echo "::error::$label failed (exitCode=$code)"
  exit 1
fi
