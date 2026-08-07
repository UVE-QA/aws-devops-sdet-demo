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
# Usage:  scripts/sweep-orphans.sh <environment>
#
# The three BREAK_TEST_ variables replace one input each with a fixture, so a
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

echo "::group::tagged in ${ENVIRONMENT}"
jq -r '.ResourceTagMappingList[].ResourceARN' "$WORK/tagged.json" || true
echo "::endgroup::"

python3 scripts/sweep_orphans.py \
  --tagged "$WORK/tagged.json" \
  --control "$WORK/control.json" \
  --state "$WORK/state.json" \
  --environment "$ENVIRONMENT"
