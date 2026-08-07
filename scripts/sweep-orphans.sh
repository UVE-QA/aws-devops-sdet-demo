#!/usr/bin/env bash
#
# The last thing a teardown does: fail the run if AWS holds a project-tagged
# resource that Terraform does not manage (ADR-0037 D4).
#
# WHY THIS IS NOT THE VERIFICATION STEP AGAIN
#
# "Verify no billable resources remain" asks four services for names beginning
# with a prefix. It is a good check and it cannot see the failure this one is
# for: a destroy that dies part way drops resources OUT OF STATE, and what is
# left is then invisible to Terraform, unmentioned by any plan, and - if it is
# not one of the four kinds asked about - unmentioned by the verification too.
# On 2026-08-06 an ECS cluster survived that way and the account was emptied by
# four manual AWS calls.
#
# So this asks the opposite question. Not "is what I know about gone?" but
# "is everything AWS still has, mine to have?".
#
# THE CONTROL IS IN THE SAME COMMAND, AND IT IS THE POINT
#
# `get-resources` answering nothing is what a clean environment looks like, and
# also what an expired token, the wrong region and a missing `tag:GetResources`
# grant look like. So the project as a WHOLE is queried too, and it can never
# legitimately be empty: the registry, the hosted zone, the dashboard and the
# self-service level are permanent and all carry `Project=aws-devops-sdet-demo`.
# An empty control is a refusal. The decision lives in `scripts/sweep_orphans.py`
# so that branch can be driven from a dictionary in `tests/unit`.
#
# TAGGED IS NOT ALIVE (ADR-0037 D4, amended 2026-08-07)
#
# The first live run of this reported twenty-three orphans in an account three
# other checks had already called empty, and all twenty-three were tombstones:
# twenty-two deregistered task-definition revisions, which AWS keeps for ever
# and `destroy` never deletes, and one INACTIVE ECS cluster, which keeps
# answering `describe` after deletion. So the tagging API is the DISCOVERY and
# the owning service is the CONFIRMATION - here, `ecs list-clusters`, which
# returns ACTIVE clusters only and is the same call the verification step makes.
#
# THE TAGGING API IS DISCOVERY, NEVER A VERDICT (2026-08-07)
#
# It was wrong in BOTH directions on the day this was written, in the same hour:
#
#   too late   run 40 seconds into a teardown, it did not report the RDS
#              instance - the only billable thing in the account - because the
#              instance was still `creating`
#   too early  run one minute after a SUCCESSFUL destroy, it reported a security
#              group that `describe-security-groups` answered
#              `InvalidGroup.NotFound` for
#
# The second is the dangerous one: it would have reddened every teardown from
# now on, and a red `destroy` job means `release-lock` keeps the lock
# (ADR-0036 D2), so the public button would have stayed shut until its TTL after
# every launch. A gate that is always red is switched off, and this one takes
# the button with it.
#
# So nothing becomes a finding until the service that OWNS it says it is there.
# Discovery is the tagging API; existence is `describe`, one call per kind. A
# kind with no rule here is still reported - fail-closed - but labelled
# `unconfirmed`, so "this exists" and "I could not check" never read the same.
#
# Usage:  scripts/sweep-orphans.sh <environment>
#
# The four BREAK_TEST_ variables replace one input each with a fixture, so a
# planted orphan and a dead credential can both be exercised without an account.

set -euo pipefail

ENVIRONMENT="${1:-}"
if [ -z "$ENVIRONMENT" ]; then
  echo "usage: $0 <environment>" >&2
  exit 2
fi

PROJECT="aws-devops-sdet-demo"
REGION="${AWS_REGION:-us-west-2}"
ENV_DIR="infra/envs/${ENVIRONMENT}"

if [ ! -d "$ENV_DIR" ]; then
  echo "::error::$ENV_DIR not found - is '$ENVIRONMENT' an environment?" >&2
  exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --- what Terraform manages -------------------------------------------------
if [ -n "${BREAK_TEST_STATE_JSON:-}" ]; then
  echo "!! BREAK_TEST_STATE_JSON is set: reading ${BREAK_TEST_STATE_JSON} instead of Terraform"
  cp "$BREAK_TEST_STATE_JSON" "$WORK/state.json"
else
  # NOT `|| true`. A state that cannot be read is not an empty state - it is a
  # missing `terraform init`, and treating it as empty would report every
  # managed resource in the environment as an orphan.
  terraform -chdir="$ENV_DIR" show -json > "$WORK/state.json"
fi

# --- what AWS is tagged with ------------------------------------------------
if [ -n "${BREAK_TEST_TAGGED_JSON:-}" ]; then
  echo "!! BREAK_TEST_TAGGED_JSON is set: reading ${BREAK_TEST_TAGGED_JSON} instead of AWS"
  cp "$BREAK_TEST_TAGGED_JSON" "$WORK/tagged.json"
else
  echo "account: $(aws sts get-caller-identity --query Account --output text)"
  aws resourcegroupstaggingapi get-resources \
    --region "$REGION" \
    --tag-filters "Key=Project,Values=${PROJECT}" "Key=Environment,Values=${ENVIRONMENT}" \
    --output json > "$WORK/tagged.json"
fi

if [ -n "${BREAK_TEST_CONTROL_JSON:-}" ]; then
  echo "!! BREAK_TEST_CONTROL_JSON is set: reading ${BREAK_TEST_CONTROL_JSON} instead of AWS"
  cp "$BREAK_TEST_CONTROL_JSON" "$WORK/control.json"
else
  # The positive control, asked with the SAME credential, in the SAME command,
  # against the SAME API. Anything else and it would be a control that can pass
  # while the real question goes unanswered.
  aws resourcegroupstaggingapi get-resources \
    --region "$REGION" \
    --tag-filters "Key=Project,Values=${PROJECT}" \
    --output json > "$WORK/control.json"
fi

# --- what the owning service says is still there ----------------------------
#
# One `describe` per ARN, and the ARN is only kept when the call SUCCEEDS. A
# call that fails for any reason - the resource is gone, the API is unhappy, the
# credential died - leaves the ARN out of `present.json`, and the decision then
# treats it as unconfirmed rather than as absent. Refusing to distinguish those
# two would be the empty-result trap again, one level down.
confirm_exists() {
  local arn="$1" region="$2"
  local service kind id
  service="$(echo "$arn" | cut -d: -f3)"
  id="$(echo "$arn" | cut -d: -f6-)"
  kind="${id%%/*}"
  case "$service:$kind" in
    ec2:security-group)
      aws ec2 describe-security-groups --region "$region" --group-ids "${id#*/}" >/dev/null 2>&1 ;;
    ec2:subnet)
      aws ec2 describe-subnets --region "$region" --subnet-ids "${id#*/}" >/dev/null 2>&1 ;;
    ec2:vpc)
      aws ec2 describe-vpcs --region "$region" --vpc-ids "${id#*/}" >/dev/null 2>&1 ;;
    ec2:internet-gateway)
      aws ec2 describe-internet-gateways --region "$region" --internet-gateway-ids "${id#*/}" >/dev/null 2>&1 ;;
    ec2:route-table)
      aws ec2 describe-route-tables --region "$region" --route-table-ids "${id#*/}" >/dev/null 2>&1 ;;
    ec2:elastic-ip)
      aws ec2 describe-addresses --region "$region" --allocation-ids "${id#*/}" >/dev/null 2>&1 ;;
    ecs:cluster)
      # ACTIVE only. A deleted cluster answers `describe` for a while, with
      # status INACTIVE, which is how one survived a teardown on 2026-08-06.
      [ "$(aws ecs describe-clusters --region "$region" --clusters "${id#*/}" \
             --query "clusters[0].status" --output text 2>/dev/null)" = "ACTIVE" ] ;;
    ecs:service)
      [ "$(aws ecs describe-services --region "$region" --cluster "$(echo "${id#*/}" | cut -d/ -f1)" \
             --services "$(echo "$id" | rev | cut -d/ -f1 | rev)" \
             --query "services[0].status" --output text 2>/dev/null)" = "ACTIVE" ] ;;
    rds:db)
      aws rds describe-db-instances --region "$region" --db-instance-identifier "${id#*:}" >/dev/null 2>&1 ;;
    rds:subgrp)
      aws rds describe-db-subnet-groups --region "$region" --db-subnet-group-name "${id#*:}" >/dev/null 2>&1 ;;
    elasticloadbalancing:loadbalancer)
      aws elbv2 describe-load-balancers --region "$region" --load-balancer-arns "$arn" >/dev/null 2>&1 ;;
    elasticloadbalancing:targetgroup)
      aws elbv2 describe-target-groups --region "$region" --target-group-arns "$arn" >/dev/null 2>&1 ;;
    logs:log-group)
      [ -n "$(aws logs describe-log-groups --region "$region" \
                --log-group-name-prefix "${id#*:}" --query "logGroups[0].arn" --output text 2>/dev/null | grep -v None)" ] ;;
    secretsmanager:secret)
      aws secretsmanager describe-secret --region "$region" --secret-id "$arn" >/dev/null 2>&1 ;;
    *)
      # No rule. `unconfirmed` is not `absent`: the ARN goes to the decision
      # marked, and the decision reports it.
      return 2 ;;
  esac
}

if [ -n "${BREAK_TEST_PRESENT_JSON:-}" ]; then
  echo "!! BREAK_TEST_PRESENT_JSON is set: reading ${BREAK_TEST_PRESENT_JSON} instead of AWS"
  cp "$BREAK_TEST_PRESENT_JSON" "$WORK/present.json"
else
  present="[]"
  unconfirmed="[]"
  while IFS= read -r arn; do
    [ -n "$arn" ] || continue
    # `|| rc=$?`, never a bare call. Under `set -e` a function returning
    # non-zero ENDS THE SCRIPT, and here non-zero is the ordinary answer: it is
    # what "the service says it is gone" looks like. The step would have gone
    # red on the first deleted resource, which is the right colour for entirely
    # the wrong reason.
    rc=0
    confirm_exists "$arn" "$REGION" || rc=$?
    case "$rc" in
      0) present="$(echo "$present" | jq -c --arg a "$arn" '. + [$a]')" ;;
      2) unconfirmed="$(echo "$unconfirmed" | jq -c --arg a "$arn" '. + [$a]')" ;;
      *) : ;;   # the service says it is not there
    esac
  done < <(jq -r '.ResourceTagMappingList[].ResourceARN' "$WORK/tagged.json")
  jq -n --argjson p "$present" --argjson u "$unconfirmed" \
    '{present: $p, unconfirmed: $u}' > "$WORK/present.json"
fi

echo "::group::tagged in ${ENVIRONMENT}"
jq -r '.ResourceTagMappingList[].ResourceARN' "$WORK/tagged.json" || true
echo "::endgroup::"

python3 scripts/sweep_orphans.py \
  --tagged "$WORK/tagged.json" \
  --control "$WORK/control.json" \
  --state "$WORK/state.json" \
  --present "$WORK/present.json" \
  --environment "$ENVIRONMENT"
