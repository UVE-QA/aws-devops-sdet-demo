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

if [ "$code" != "0" ]; then
  echo "::error::$label failed (exitCode=$code)"
  exit 1
fi
