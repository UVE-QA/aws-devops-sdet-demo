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
# The five BREAK_TEST_ variables replace one input each with a fixture, so a
# planted orphan and a dead credential can both be exercised without an account.
# BREAK_TEST_UNINDEXED_JSON is the newest: it stands in for what the
# configuration declares, and an empty `names` list there is how the second
# channel's own refusal is exercised (ADR-0041 D4).

set -euo pipefail

ENVIRONMENT="${1:-}"
if [ -z "$ENVIRONMENT" ]; then
  echo "usage: $0 <environment>" >&2
  exit 2
fi

PROJECT="aws-devops-sdet-demo"
PREFIX="${PROJECT}-${ENVIRONMENT}"
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
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
  echo "account: $ACCOUNT"
  aws resourcegroupstaggingapi get-resources \
    --region "$REGION" \
    --tag-filters "Key=Project,Values=${PROJECT}" "Key=Environment,Values=${ENVIRONMENT}" \
    --output json > "$WORK/tagged.json"
fi

# --- what the tagging API cannot see at all (ADR-0041) -----------------------
#
# The second discovery channel, and it asks the CONFIGURATION rather than AWS.
# `iam:role` is not in the tagging API's index - `iam:oidc-provider` is, from the
# same state level with the same tags, which is how this was told apart from a
# wrong region - so a role left behind by a teardown is invisible to the query
# above, to `Verify no billable resources remain` (a role is free), and to
# Terraform, which no longer holds it. Two of them blocked every apply for three
# days after a teardown that verified itself green.
#
# There is nothing to scan with either: the deploy role has `iam:GetRole` on two
# ARNs and neither `iam:ListRoles` nor `iam:ListRoleTags`. So the names come from
# `adopt_orphans.py`, which already holds the map of what this configuration has,
# and the loop below asks the owning service about each. A name that exists and
# is not in state is an orphan; a name that does not exist is what a finished
# teardown looks like.
if [ -n "${BREAK_TEST_UNINDEXED_JSON:-}" ]; then
  echo "!! BREAK_TEST_UNINDEXED_JSON is set: reading ${BREAK_TEST_UNINDEXED_JSON} instead of the configuration"
  cp "$BREAK_TEST_UNINDEXED_JSON" "$WORK/declared.json"
else
  python3 scripts/adopt_orphans.py --unindexed "$PREFIX" \
    --account "${ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}" \
    > "$WORK/declared.json"
fi

# One file from here on: the decision, the log and the adoption step all work
# from everything discovery found, by whichever channel.
jq -c --slurpfile d "$WORK/declared.json" \
  '.ResourceTagMappingList += [$d[0].names[] | {ResourceARN: .arn, Tags: []}]' \
  "$WORK/tagged.json" > "$WORK/discovered.json"

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
  local parsed key id
  # PARSED BY scripts/arns.py, not here. This function used to compute the kind
  # as `${id%%/*}` - up to the first SLASH - which is right for
  # `security-group/sg-0abc` and wrong for every ARN whose resource part is
  # COLON-separated: `db:demo-db` came back whole as the kind, so `rds:db`,
  # `rds:subgrp`, `logs:log-group` and `secretsmanager:secret` were four arms
  # that had never once been reached. Every resource of those kinds answered
  # `unconfirmed`, which is honest and unhelpful, and looks in a log exactly
  # like a kind nobody thought about.
  #
  # It was invisible on an empty account, which is where it was tested: nothing
  # of those kinds is tagged once the environment is gone. On 2026-08-07 a
  # cancelled launch left an RDS instance alive, the sweep could not confirm it,
  # the adoption step rightly refused to import something nobody had confirmed,
  # and the destroy died on the subnet group it was holding.
  parsed="$(python3 scripts/arns.py "$arn")" || return 2
  key="${parsed%%$'\t'*}"
  id="${parsed#*$'\t'}"
  case "$key" in
    ec2:security-group)
      aws ec2 describe-security-groups --region "$region" --group-ids "$id" >/dev/null 2>&1 ;;
    ec2:subnet)
      aws ec2 describe-subnets --region "$region" --subnet-ids "$id" >/dev/null 2>&1 ;;
    ec2:vpc)
      aws ec2 describe-vpcs --region "$region" --vpc-ids "$id" >/dev/null 2>&1 ;;
    ec2:internet-gateway)
      aws ec2 describe-internet-gateways --region "$region" --internet-gateway-ids "$id" >/dev/null 2>&1 ;;
    ec2:route-table)
      aws ec2 describe-route-tables --region "$region" --route-table-ids "$id" >/dev/null 2>&1 ;;
    ec2:elastic-ip)
      aws ec2 describe-addresses --region "$region" --allocation-ids "$id" >/dev/null 2>&1 ;;
    ecs:task-definition)
      # NEVER present, and by KIND rather than by status. A revision no service
      # refers to is inert whether it is ACTIVE or INACTIVE: nothing runs from
      # it, `terraform destroy` can only DEREGISTER one, and AWS keeps the
      # record indefinitely at no cost. There is no state in which one is worth
      # acting on, so a status check here would only produce a rule that fires
      # on something nobody can use.
      #
      # This was learned twice. First as an exclusion list, then removed on the
      # theory that confirmation subsumed it - which turned 22 revisions from
      # excluded into `unconfirmed`, and the gate red, in an empty account.
      return 1 ;;
    ecs:cluster)
      # ACTIVE only. A deleted cluster answers `describe` for a while, with
      # status INACTIVE, which is how one survived a teardown on 2026-08-06.
      [ "$(aws ecs describe-clusters --region "$region" --clusters "$id" \
             --query "clusters[0].status" --output text 2>/dev/null)" = "ACTIVE" ] ;;
    ecs:service)
      [ "$(aws ecs describe-services --region "$region" --cluster "${id%%/*}" \
             --services "${id##*/}" \
             --query "services[0].status" --output text 2>/dev/null)" = "ACTIVE" ] ;;
    rds:db)
      aws rds describe-db-instances --region "$region" --db-instance-identifier "$id" >/dev/null 2>&1 ;;
    rds:subgrp)
      aws rds describe-db-subnet-groups --region "$region" --db-subnet-group-name "$id" >/dev/null 2>&1 ;;
    elasticloadbalancing:loadbalancer)
      aws elbv2 describe-load-balancers --region "$region" --load-balancer-arns "$arn" >/dev/null 2>&1 ;;
    elasticloadbalancing:targetgroup)
      aws elbv2 describe-target-groups --region "$region" --target-group-arns "$arn" >/dev/null 2>&1 ;;
    cloudwatch:alarm)
      # Both of these appeared for the first time on 2026-08-07, in the first
      # sweep this project ever ran against a LIVE environment rather than the
      # remains of one. Neither is adoptable and neither needs to be - a
      # listener leaves with its load balancer - but `unconfirmed` is red, and a
      # gate that reddens on a resource behaving perfectly normally is a gate on
      # its way to being switched off.
      [ "$(aws cloudwatch describe-alarms --region "$region" --alarm-names "$id" \
             --query "MetricAlarms[0].AlarmName" --output text 2>/dev/null)" = "$id" ] ;;
    elasticloadbalancing:listener)
      aws elbv2 describe-listeners --region "$region" --listener-arns "$arn" >/dev/null 2>&1 ;;
    logs:log-group)
      [ -n "$(aws logs describe-log-groups --region "$region" \
                --log-group-name-prefix "$id" --query "logGroups[0].arn" --output text 2>/dev/null | grep -v None)" ] ;;
    secretsmanager:secret)
      aws secretsmanager describe-secret --region "$region" --secret-id "$arn" >/dev/null 2>&1 ;;
    iam:role)
      # THE ONLY ARM THAT SEPARATES "it is gone" FROM "I could not ask", and the
      # only one that has to (ADR-0041 D4). Every arm above returns non-zero for
      # both, which is safe there for a reason that does not hold here: the
      # tagging API had already proved the credential works by returning the ARN
      # in the first place. This kind is discovered from the CONFIGURATION, so
      # nothing has been proved about the credential, and an AccessDenied would
      # otherwise read exactly like a role that is not there - the empty-result
      # trap, one level below the one this file already guards.
      #
      # IAM is global; no --region, deliberately, rather than a region that would
      # be ignored and look meaningful.
      err="$(aws iam get-role --role-name "$id" 2>&1 >/dev/null)" && return 0
      case "$err" in
        *NoSuchEntity*) return 1 ;;
        *) echo "::warning::get-role could not answer for ${id}: ${err}" >&2; return 2 ;;
      esac ;;
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
  done < <(jq -r '.ResourceTagMappingList[].ResourceARN' "$WORK/discovered.json")
  jq -n --argjson p "$present" --argjson u "$unconfirmed" \
    '{present: $p, unconfirmed: $u}' > "$WORK/present.json"
fi

# Printed per CHANNEL. A single list would hide which question found what, and
# the whole finding behind ADR-0041 is that one of the two questions was not
# being asked at all.
echo "::group::discovered in ${ENVIRONMENT}"
echo "-- tagging API, Project + Environment"
jq -r '.ResourceTagMappingList[].ResourceARN' "$WORK/tagged.json" || true
echo "-- the configuration, for kinds the tagging API does not index"
jq -r '.names[] | "\(.arn)   (\(.kind))"' "$WORK/declared.json" || true
echo "::endgroup::"

# SWEEP_KEEP_DIR is how `scripts/adopt-orphans.sh` gets at the answer without
# asking AWS a second time (ADR-0038 D2). Everything this run looked at is
# copied there, including the tags, which adoption needs and the decision drops.
# The exit code is captured rather than allowed to end the script, because the
# copy below has to happen either way: a RED sweep is exactly the case adoption
# has work to do in. The code is re-raised at the end, so this script's contract
# to every existing caller is unchanged.
DECIDE=(python3 scripts/sweep_orphans.py
  --tagged "$WORK/discovered.json"
  --control "$WORK/control.json"
  --declared "$WORK/declared.json"
  --state "$WORK/state.json"
  --present "$WORK/present.json"
  --environment "$ENVIRONMENT")
if [ -n "${SWEEP_KEEP_DIR:-}" ]; then
  DECIDE+=(--json "$WORK/decision.json")
fi

RC=0
"${DECIDE[@]}" || RC=$?

if [ -n "${SWEEP_KEEP_DIR:-}" ]; then
  mkdir -p "$SWEEP_KEEP_DIR"
  cp "$WORK"/*.json "$SWEEP_KEEP_DIR/"
fi

exit "$RC"
