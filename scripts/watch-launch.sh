#!/usr/bin/env bash
#
# Watch one self-service launch from OUTSIDE it, and leave a log that can be
# read afterwards as evidence.
#
# WHY THIS IS A SCRIPT AND NOT A LOOP TYPED INTO A TERMINAL
#
# It was typed into a terminal on three separate days, and both of its failure
# modes are written down in docs/sessions/2026-08-07-phase-19g-*:
#
#   started outside the repository   `gh run list` answered "failed to determine
#                                    base repo" on every tick, so the run column
#                                    was empty for the whole launch
#   run in the foreground            an SSH disconnect took it with it, and the
#                                    log has a 2h46m hole in the middle of the
#                                    phase it was recording
#
# Neither is a property of the loop. Both are properties of WHERE and HOW it was
# started, which is why they recur every time it is started again - so they
# belong inside the thing being started. This script cds to the repository
# itself; running it under `nohup` covers the second.
#
# NOTHING HERE MAY PRINT AN EMPTY FIELD WHEN A CALL FAILS
#
# `alb=none` is what a torn-down environment looks like. It is also what an
# expired token, the wrong region and a missing grant look like, and this
# project has already read nine empty lines as a clean account once. So every
# field is either a value or `ERR`, never blank - and `acct` is re-read on EVERY
# tick rather than once at the top, because a credential that dies at 00:40 has
# to make the log say so at 00:40 rather than quietly turning the rest of the
# run into `none`.
#
# It is READ-ONLY. It creates nothing, deletes nothing and dispatches nothing:
# the point of the phase it was written for is that nobody is in the loop.
#
# Usage:
#   scripts/watch-launch.sh [interval_seconds]        # default 20
#
#   nohup scripts/watch-launch.sh > /tmp/watch.log 2>&1 &
#   tail -f /tmp/watch.log
#
# ONE `tail -f` per file. Two of them interleave, and the output then reads as
# though the clock went backwards - also learned on 2026-08-07.

# NOT `set -e`: a loop that exits on the first transient AWS error stops the
# evidence at exactly the moment something interesting was happening. Failures
# are reported per field instead, as ERR. pipefail matters because every getter
# ends in a pipe, and without it a failed `aws` would be laundered into an empty
# string by `tr`, which is the blank field this script exists to refuse.
set -uo pipefail

# `gh` resolves the repository from the working directory. See the header.
cd "$(dirname "$0")/.." || exit 1

INTERVAL="${1:-20}"
PROJECT="aws-devops-sdet-demo"
ENVIRONMENT="${ENVIRONMENT:-stage}"
PREFIX="${PROJECT}-${ENVIRONMENT}"
REGION="${AWS_REGION:-us-west-2}"
PROFILE="${AWS_PROFILE:-demo-admin}"
TABLE="${PROJECT}-self-service-control"

a() { aws --profile "$PROFILE" --region "$REGION" "$@"; }

# A value, or `none`, or `ERR`. Never blank.
field() {
  local out
  if ! out="$("$@" 2>/dev/null)"; then
    echo "ERR"
    return
  fi
  if [ -z "${out//[[:space:]]/}" ]; then
    echo "none"
    return
  fi
  echo "$out"
}

get_account() { a sts get-caller-identity --query Account --output text; }

get_alb() {
  a elbv2 describe-load-balancers \
    --query "LoadBalancers[?starts_with(LoadBalancerName,'$PREFIX')].[LoadBalancerName,State.Code]" \
    --output text | tr '\n\t' '  '
}

# The status, not just the name. Deciding WHEN to cancel needs `creating` vs
# `available`, and an instance adopted while still creating is defect 2 of 19g.
get_rds() {
  a rds describe-db-instances \
    --query "DBInstances[?starts_with(DBInstanceIdentifier,'$PREFIX')].[DBInstanceIdentifier,DBInstanceStatus]" \
    --output text | tr '\n\t' '  '
}

# ACTIVE only - the same call the teardown's verification makes. A deleted
# cluster answers `describe` for ever, so `list-clusters` is the honest one.
get_ecs() { a ecs list-clusters --query 'clusterArns[]' --output text | tr '\n\t' '  '; }

get_sg() {
  a ec2 describe-security-groups \
    --filters "Name=tag:Project,Values=$PROJECT" \
    --query 'SecurityGroups[].GroupName' --output text | tr '\n\t' '  '
}

# The control store, minus the nonces, which are single-use and noisy. `lock`
# appearing and leaving is the launch's own record of itself.
get_store() {
  a dynamodb scan --table-name "$TABLE" \
    --filter-expression 'NOT begins_with(pk, :n)' \
    --expression-attribute-values '{":n":{"S":"nonce#"}}' \
    --query 'Items[].pk.S' --output text | tr '\n\t' '  '
}

get_run() {
  gh run list --workflow self-service.yml --limit 1 \
    --json databaseId,status,conclusion \
    --jq '.[] | "\(.databaseId) \(.status)/\(.conclusion // "-")"'
}

echo "watch: $(date -u +%FT%TZ) env=$ENVIRONMENT region=$REGION profile=$PROFILE interval=${INTERVAL}s"

# Refuse at the top rather than log a row of `none` for every field. This is the
# only exit: after this, the loop reports failures and keeps watching.
acct="$(get_account 2>/dev/null)" || acct=""
if [ -z "$acct" ]; then
  echo "watch: no usable credentials. Refusing to record an account that would read as empty." >&2
  exit 1
fi
echo "watch: account $acct"

while :; do
  printf '%s | acct=%s | alb=%s | rds=%s | ecs=%s | sg=%s | store=%s | run=%s\n' \
    "$(date -u +%T)" \
    "$(field get_account)" \
    "$(field get_alb)" \
    "$(field get_rds)" \
    "$(field get_ecs)" \
    "$(field get_sg)" \
    "$(field get_store)" \
    "$(field get_run)"
  sleep "$INTERVAL"
done
