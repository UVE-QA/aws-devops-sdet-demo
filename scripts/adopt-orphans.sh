#!/usr/bin/env bash
#
# Adopt live, unmanaged resources into Terraform state, so the destroy that
# follows can remove them and everything that depends on them (ADR-0038).
#
# WHAT THIS IS FOR
#
# A cancelled apply creates resources that never enter state. Terraform then
# cannot delete them, and cannot delete what depends on them: on 2026-08-07 an
# unmanaged RDS instance held a managed DB subnet group and the destroy died on
# that pair in 70 seconds, twice. The blunt path removed the instance an hour
# later - which is precisely what unblocks Terraform - and nothing ran Terraform
# again. The remainder took three manual AWS calls.
#
# So the teardown adopts first. It runs on EVERY teardown, not only after a
# failure: on a healthy environment it finds nothing and costs a few seconds,
# and a path that only runs after a disaster is a path nobody has exercised.
#
# ITS INPUT IS THE GATE, NOT A SECOND OPINION
#
# `scripts/sweep-orphans.sh` already decides what is live and unmanaged, with
# the three classes ADR-0037 settled on after the tagging API was wrong in both
# directions inside one hour. This script RUNS it and adopts exactly what it
# reports. One definition of "orphan", in one place; the check that names the
# remainder is the input to the thing that removes it.
#
# `SWEEP_KEEP_DIR` is how the answer comes back - including the tags, which the
# decision drops and the address map needs - without asking AWS a second time.
#
# WHAT IT REFUSES, AND THE ONE THING IT DOES NOT
#
#   the sweep refused          exit 2. Its positive control came back empty,
#                              which means the question was not answered. Acting
#                              on an unanswered question is the empty-result
#                              trap with an import attached
#   no rule / no Name tag /    printed as UNADOPTABLE and left alone. The
#   unknown name / a clash     end-of-run sweep is what fails on them
#   an import that fails       printed with its error, and the script CONTINUES
#
# The last one is a deliberate exception to fail-closed and it needs its reason
# written down: this step exists so the destroy after it succeeds, and a step
# that aborts leaves the billable resources running for another TTL. The run's
# colour is still decided by the two gates at the end, which are unchanged.
#
# Usage:  scripts/adopt-orphans.sh <environment>
#
# BREAK_TEST_PLAN_JSON replaces the whole discovery with a fixture, so the
# import loop can be driven without an account.

set -euo pipefail

ENVIRONMENT="${1:-}"
if [ -z "$ENVIRONMENT" ]; then
  echo "usage: $0 <environment>" >&2
  exit 2
fi

ENV_DIR="infra/envs/${ENVIRONMENT}"
if [ ! -d "$ENV_DIR" ]; then
  echo "::error::$ENV_DIR not found - is '$ENVIRONMENT' an environment?" >&2
  exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -n "${BREAK_TEST_PLAN_JSON:-}" ]; then
  echo "!! BREAK_TEST_PLAN_JSON is set: reading ${BREAK_TEST_PLAN_JSON} instead of AWS"
  cp "$BREAK_TEST_PLAN_JSON" "$WORK/plan.json"
else
  echo "::group::what the sweep sees before the teardown"
  # NOT under `set -e`. A red sweep is the case this script exists for, and a
  # green one is the ordinary teardown - both are expected answers, and neither
  # is this script's verdict.
  SWEEP_RC=0
  SWEEP_KEEP_DIR="$WORK" scripts/sweep-orphans.sh "$ENVIRONMENT" || SWEEP_RC=$?
  echo "::endgroup::"
  echo "sweep exit: $SWEEP_RC"

  if [ ! -f "$WORK/decision.json" ]; then
    echo "::error::the sweep wrote no decision - nothing to adopt on" >&2
    exit 2
  fi

  # `discovered.json`, not `tagged.json`: since ADR-0041 the sweep has two
  # discovery channels and this is the merged answer. Adopting from the tagging
  # API's half alone would refuse to import exactly the orphan that motivated
  # the second channel.
  python3 scripts/adopt_orphans.py \
    --decision "$WORK/decision.json" \
    --tagged "$WORK/discovered.json" \
    --environment "$ENVIRONMENT" \
    --out "$WORK/plan.json"
fi

COUNT="$(jq '.adopt | length' "$WORK/plan.json")"
if [ "$COUNT" -eq 0 ]; then
  echo "nothing to adopt; the teardown proceeds"
  exit 0
fi

echo "adopting $COUNT resource(s) into infra/envs/${ENVIRONMENT}"
FAILED=0
while IFS=$'\t' read -r ADDRESS IMPORT_ID; do
  [ -n "$ADDRESS" ] || continue
  echo "::group::terraform import $ADDRESS"
  # `|| rc=$?`, never a bare call: under `set -e` the first import that fails
  # would end the script, and this loop is written on the assumption that some
  # of them will.
  RC=0
  terraform -chdir="$ENV_DIR" import -input=false "$ADDRESS" "$IMPORT_ID" || RC=$?
  echo "::endgroup::"
  if [ "$RC" -ne 0 ]; then
    echo "::warning::could not adopt $ADDRESS ($IMPORT_ID) - exit $RC"
    FAILED=$((FAILED + 1))
  else
    echo "adopted $ADDRESS"
  fi
done < <(jq -r '.adopt[] | [.address, .import_id] | @tsv' "$WORK/plan.json")

echo "-----"
echo "adopted $((COUNT - FAILED)) of $COUNT; $FAILED could not be imported"
# Zero on purpose, even with failures. See the header: the destroy after this
# is the point, and the gates at the end are what judge the result.
exit 0
