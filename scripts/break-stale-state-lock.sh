#!/usr/bin/env bash
#
# Break a Terraform state lock that a FINISHED run left behind, and refuse in
# every other case (ADR-0036 D3).
#
# WHY THIS EXISTS
#
# A run cancelled mid-apply leaves the S3 lockfile held. Nothing releases it:
# the runner is gone. `destroy` then waits for a lock nobody will ever release,
# the watchdog re-dispatches a destroy that dies the same way, and the recovery
# written down in `watchdog_handler.py` - "re-run destroy" - cannot work. On
# 2026-08-05 that cost two fifteen-minute timeouts and ended in a human running
# `force-unlock` by hand while an ALB and an RDS instance billed.
#
# WHAT MAKES THIS SAFE TO RUN ON EVERY TEARDOWN
#
# Two writers on one state file is the one failure this project has never had,
# and an unconditional force-unlock would be a self-inflicted one. So this
# refuses unless BOTH of these hold:
#
#   1. the lock was taken by the same user this script is running as. Terraform
#      writes `user@host` into the lockfile; a GitHub-hosted runner is
#      `runner@...` and this project's devbox is `ubuntu@...`. A human's lock is
#      never the system's to break. This is evidence about the holder, not a
#      guess about how long an apply ought to take - which is why there is no
#      age threshold here.
#   2. no OTHER run of this repository is in progress. If something is running,
#      something may legitimately hold it.
#
# Anything unreadable, missing or ambiguous is a refusal. The usual direction.
#
# Usage:  scripts/break-stale-state-lock.sh <environment>
#
# The two BREAK_TEST_ variables below exist so the refusals can be exercised on
# fixtures instead of by cancelling a real apply. They are printed loudly when
# set, so a production run that somehow has them is visible in its own log.

set -euo pipefail

ENVIRONMENT="${1:-}"
if [ -z "$ENVIRONMENT" ]; then
  echo "usage: $0 <environment>" >&2
  exit 2
fi

ENV_DIR="infra/envs/${ENVIRONMENT}"
BACKEND="${ENV_DIR}/backend.tf"

if [ ! -f "$BACKEND" ]; then
  echo "::error::$BACKEND not found - is '$ENVIRONMENT' an environment?" >&2
  exit 2
fi

# One definition. The bucket and key are read out of the backend block rather
# than repeated here, so this cannot drift away from the state it protects.
BUCKET="$(sed -n 's/^[[:space:]]*bucket[[:space:]]*=[[:space:]]*"\(.*\)".*/\1/p' "$BACKEND" | head -1)"
KEY="$(sed -n 's/^[[:space:]]*key[[:space:]]*=[[:space:]]*"\(.*\)".*/\1/p' "$BACKEND" | head -1)"

if [ -z "$BUCKET" ] || [ -z "$KEY" ]; then
  echo "::error::could not read bucket/key from $BACKEND" >&2
  exit 2
fi

LOCK_KEY="${KEY}.tflock"
echo "state lock object: s3://${BUCKET}/${LOCK_KEY}"

LOCKFILE="$(mktemp)"
trap 'rm -f "$LOCKFILE"' EXIT

if [ -n "${BREAK_TEST_LOCKFILE:-}" ]; then
  echo "!! BREAK_TEST_LOCKFILE is set: reading ${BREAK_TEST_LOCKFILE} instead of S3"
  if [ ! -f "$BREAK_TEST_LOCKFILE" ]; then
    echo "no lockfile fixture at $BREAK_TEST_LOCKFILE - nothing to break."
    exit 0
  fi
  cp "$BREAK_TEST_LOCKFILE" "$LOCKFILE"
elif aws s3api get-object --bucket "$BUCKET" --key "$LOCK_KEY" "$LOCKFILE" >/dev/null 2>&1; then
  :
else
  # The normal path, on every teardown that did not follow a cancelled run.
  echo "no state lock is held. Nothing to break."
  exit 0
fi

echo "::group::the lockfile, in full"
cat "$LOCKFILE"
echo
echo "::endgroup::"

ID="$(jq -r '.ID // empty' "$LOCKFILE" 2>/dev/null || true)"
WHO="$(jq -r '.Who // empty' "$LOCKFILE" 2>/dev/null || true)"
CREATED="$(jq -r '.Created // "unknown"' "$LOCKFILE" 2>/dev/null || echo unknown)"

if [ -z "$ID" ]; then
  echo "::error::the lockfile has no readable ID. Breaking a lock we cannot name is not a controlled operation - refusing."
  exit 1
fi

ME="$(id -un)"
LOCK_USER="${WHO%%@*}"
if [ -z "$WHO" ] || [ "$LOCK_USER" != "$ME" ]; then
  echo "::error::the lock is held by '${WHO:-<unknown>}' and this job runs as '${ME}'. A lock taken by someone else - a devbox apply, a different runner image - is not ours to break. Refusing."
  exit 1
fi

if [ -n "${BREAK_TEST_RUNS_IN_PROGRESS:-}" ]; then
  echo "!! BREAK_TEST_RUNS_IN_PROGRESS is set to ${BREAK_TEST_RUNS_IN_PROGRESS}: not asking the API"
  OTHERS="$BREAK_TEST_RUNS_IN_PROGRESS"
else
  # Needs `actions: read`. A missing token or a failed call leaves OTHERS empty,
  # and empty is treated as "cannot tell", which refuses: an API answering
  # nothing is not evidence that there is nothing.
  #
  # `${VAR:-}` on both, deliberately. Running this outside Actions with `set -u`
  # used to abort on "GITHUB_REPOSITORY: unbound variable" - the right exit code
  # for the wrong reason, and a message that names a shell variable instead of
  # the refusal. Found by running it outside Actions, which is where it will be
  # run again the next time someone is debugging a stuck lock.
  OTHERS="$(gh api "repos/${GITHUB_REPOSITORY:-}/actions/runs?status=in_progress&per_page=100" \
              --jq "[.workflow_runs[] | select(.id != ${GITHUB_RUN_ID:-0}) ] | length" 2>/dev/null || true)"
fi

if ! [ "${OTHERS:-}" -eq "${OTHERS:-}" ] 2>/dev/null; then
  echo "::error::could not find out whether other runs are in progress. Refusing rather than guessing."
  exit 1
fi

if [ "$OTHERS" -ne 0 ]; then
  echo "::error::${OTHERS} other run(s) of this repository are in progress; one of them may legitimately hold this lock. Refusing."
  exit 1
fi

echo "the lock was taken by ${WHO} at ${CREATED}, no other run is in progress: breaking it."
terraform -chdir="$ENV_DIR" force-unlock -force "$ID"
echo "state lock ${ID} released. The destroy in front of this can now run."
