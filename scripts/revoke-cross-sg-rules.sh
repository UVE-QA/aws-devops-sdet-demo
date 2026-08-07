#!/usr/bin/env bash
#
# Revoke the rules by which one of this environment's security groups
# references another, so that no security group deletion is impossible by
# construction (ADR-0037 D2).
#
# WHY THIS EXISTS
#
# The environment's groups form a chain:
#
#     rds-sg  ingress <- app-sg
#     app-sg  ingress <- alb-sg
#
# AWS refuses to delete a group while another group's rule references it. The
# ALB destroy was already narrowed to `module.alb.aws_lb.this` for this reason,
# but the chain survives every partial teardown: whenever the referrer sits
# outside whatever is being destroyed, the referenced group cannot go, Terraform
# retries the deletion for fifteen minutes, and the step behind it never runs.
# That is the 15m22s failure of 2026-08-06 and the 15m40s failures of
# 2026-08-05 - the same defect, read the first time as a consequence of the
# state lock.
#
# Revoking the rules first removes the impossibility rather than waiting it out.
# The groups themselves leave with the destroy, together with the rules that the
# next apply would recreate.
#
# THIS BREAKS THE ENVIRONMENT, ON PURPOSE
#
# After this runs the ALB cannot reach the app and the app cannot reach the
# database. That is acceptable in exactly one place - a teardown, whose next
# step deletes all three - and nowhere else. It is why this script is wired into
# the teardown path only, and why it has no mode that would be safe to point at
# a live environment.
#
# WHAT IT REFUSES
#
#   - a credential that cannot answer `sts get-caller-identity`. An expired
#     token makes the describe below return nothing, and nothing is exactly what
#     an already-clean environment looks like
#   - a revoke that fails for any reason other than "the rule is not there".
#     Continuing would hand the fifteen-minute retry back to Terraform while
#     this log claimed the preflight had dealt with it
#
# Finding NO groups is not a refusal: an environment already destroyed, or never
# created, has none, and this runs on every teardown including those.
#
# Usage:  scripts/revoke-cross-sg-rules.sh <environment>
#
# BREAK_TEST_SG_JSON replaces the describe call with a fixture, so the decision
# can be exercised without an environment; BREAK_TEST_DRY_RUN prints the revokes
# instead of making them. Both are printed loudly when set.

set -euo pipefail

ENVIRONMENT="${1:-}"
if [ -z "$ENVIRONMENT" ]; then
  echo "usage: $0 <environment>" >&2
  exit 2
fi

PROJECT="aws-devops-sdet-demo"
REGION="${AWS_REGION:-us-west-2}"

DESCRIBE="$(mktemp)"
trap 'rm -f "$DESCRIBE"' EXIT

if [ -n "${BREAK_TEST_SG_JSON:-}" ]; then
  echo "!! BREAK_TEST_SG_JSON is set: reading ${BREAK_TEST_SG_JSON} instead of EC2"
  if [ ! -f "$BREAK_TEST_SG_JSON" ]; then
    echo "::error::no fixture at $BREAK_TEST_SG_JSON - refusing to read a missing file as an empty environment."
    exit 2
  fi
  cp "$BREAK_TEST_SG_JSON" "$DESCRIBE"
else
  # `sts` first, and its answer is PRINTED rather than discarded: a check whose
  # credentials have expired prints empty lines, and empty lines are what a
  # clean environment looks like. Under `set -e` a failure here ends the script
  # instead of rendering it green.
  echo "account: $(aws sts get-caller-identity --query Account --output text)"

  aws ec2 describe-security-groups \
    --region "$REGION" \
    --filters "Name=tag:Project,Values=${PROJECT}" \
              "Name=tag:Environment,Values=${ENVIRONMENT}" \
    --output json > "$DESCRIBE"
fi

GROUP_COUNT="$(jq '.SecurityGroups | length' "$DESCRIBE")"
if [ "$GROUP_COUNT" -eq 0 ]; then
  echo "no ${PROJECT}/${ENVIRONMENT} security groups exist. Nothing to revoke."
  exit 0
fi

echo "::group::the ${GROUP_COUNT} security groups this environment has"
jq -r '.SecurityGroups[] | "\(.GroupId)  \(.GroupName)"' "$DESCRIBE"
echo "::endgroup::"

# One pass in jq, so the decision is a function of the describe output rather
# than of a shell loop's memory of it. For every group in the set, every
# permission naming ANOTHER GROUP IN THE SAME SET becomes one revoke, carrying
# the matching pairs ONLY: a permission with both a CIDR and a group pair must
# lose the pair and keep the CIDR, or the revoke would take away more than the
# reference chain.
OURS="$(jq -c '[.SecurityGroups[].GroupId]' "$DESCRIBE")"
REVOKES="$(jq -c --argjson ours "$OURS" '
  .SecurityGroups[]
  | .GroupId as $gid
  | {ingress: .IpPermissions, egress: .IpPermissionsEgress}
  | to_entries[]
  | .key as $direction
  | .value[]
  | . as $perm
  | ([ .UserIdGroupPairs[]? | select(.GroupId as $ref | $ours | index($ref)) ]) as $pairs
  | select($pairs | length > 0)
  | {
      group_id: $gid,
      direction: $direction,
      permission: ($perm
                   | .UserIdGroupPairs = $pairs
                   | del(.IpRanges, .Ipv6Ranges, .PrefixListIds))
    }
' "$DESCRIBE")"

if [ -z "$REVOKES" ]; then
  echo "no security group in this environment references another. Nothing to revoke."
  exit 0
fi

echo "::group::the cross-group rules to revoke"
echo "$REVOKES" | jq -r '"\(.direction) on \(.group_id) <- \(.permission.UserIdGroupPairs[].GroupId)"'
echo "::endgroup::"

revoked=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  gid="$(echo "$line" | jq -r '.group_id')"
  direction="$(echo "$line" | jq -r '.direction')"
  perm="$(echo "$line" | jq -c '[.permission]')"

  if [ "$direction" = "ingress" ]; then
    verb="revoke-security-group-ingress"
  else
    verb="revoke-security-group-egress"
  fi

  if [ -n "${BREAK_TEST_DRY_RUN:-}" ]; then
    echo "!! BREAK_TEST_DRY_RUN: would run aws ec2 ${verb} --group-id ${gid} --ip-permissions ${perm}"
    revoked=$((revoked + 1))
    continue
  fi

  # `|| true` on the call and the verdict taken from its OUTPUT, because the one
  # acceptable failure has to be told apart from every other one.
  # InvalidPermission.NotFound means a previous run of this step, or the destroy
  # itself, already took the rule away - which is success. Anything else is a
  # refusal.
  err="$(aws ec2 "$verb" --region "$REGION" --group-id "$gid" \
           --ip-permissions "$perm" 2>&1 >/dev/null || true)"
  if [ -z "$err" ]; then
    echo "revoked ${direction} on ${gid}"
    revoked=$((revoked + 1))
  elif echo "$err" | grep -q "InvalidPermission.NotFound"; then
    echo "already gone: ${direction} on ${gid}"
  else
    echo "::error::could not revoke ${direction} on ${gid}: ${err}"
    exit 1
  fi
done <<< "$REVOKES"

echo "-----"
echo "${revoked} cross-group rule(s) revoked. No security group deletion in ${ENVIRONMENT} is now blocked by another group."
