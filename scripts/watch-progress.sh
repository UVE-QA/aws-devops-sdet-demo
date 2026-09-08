#!/usr/bin/env bash
# Publish a partial reading of a running apply, every few seconds, until told to
# stop (ADR-0076).
#
#   scripts/watch-progress.sh <environment> &
#   echo $! > /tmp/progress.pid
#   ... terraform apply ...
#   kill "$(cat /tmp/progress.pid)"
#
# Or, preferred in a workflow, by the stop file - a kill leaves the question of
# whether the last write finished, and a job step that ends is not always a
# process that ended:
#
#   PROGRESS_STOP=/tmp/progress.stop scripts/watch-progress.sh stage &
#   ...
#   touch /tmp/progress.stop
#
# THIS LOOP MUST NEVER FAIL THE JOB IT WATCHES. It is an instrument reporting on
# an apply, not a step of it: a fold that trips over a half-written line, an S3
# PUT that times out, a stream directory that does not exist yet - none of those
# are reasons to stop a deployment. Every iteration is wrapped and every failure
# is counted and printed, so a loop that published nothing for eleven minutes
# says so in the job log rather than looking like a loop that had nothing to say.
#
# WHY IT POLLS RATHER THAN FOLLOWS THE STREAM. `tf-stream.sh` tees terraform's
# stdout to a file as it goes, so the file is always readable and always a prefix
# of the whole stream. Folding that prefix on a timer reuses scripts/
# fold-timeline.py and scripts/node-states.py EXACTLY as the end of the job uses
# them - the join rule that decides which resource belongs to which node stays in
# one place. A follower would have to hold that rule itself, incrementally, which
# is the same rule in a second implementation.
#
# Environment:
#   SITE_BUCKET       required, by publish-progress.sh
#   TF_STREAM_DIR     required, where tf-stream.sh drops its streams
#   PROGRESS_EVERY    optional, seconds between readings. Default 15.
#   PROGRESS_STOP     optional, a path whose existence ends the loop
#   TOPOLOGY_JSON     optional, default site/data/topology.json
set -uo pipefail
cd "$(dirname "$0")/.."

env_name="${1:?usage: watch-progress.sh <environment>}"
: "${SITE_BUCKET:?SITE_BUCKET is not set}"
: "${TF_STREAM_DIR:?TF_STREAM_DIR is not set}"
every="${PROGRESS_EVERY:-15}"
stop="${PROGRESS_STOP:-}"
topology="${TOPOLOGY_JSON:-site/data/topology.json}"

work="$(mktemp -d)"
published=0
failed=0

# The stop file wins over the sleep, so a job that finishes eight seconds into a
# fifteen-second wait does not hold the step open for the other seven.
nap() {
  local left="$every"
  while [ "$left" -gt 0 ]; do
    [ -n "$stop" ] && [ -e "$stop" ] && return 1
    sleep 1
    left=$((left - 1))
  done
  return 0
}

echo "watch-progress: ${env_name}, every ${every}s, streams in ${TF_STREAM_DIR}"

while :; do
  [ -n "$stop" ] && [ -e "$stop" ] && break

  # Nothing to read yet is the NORMAL first state: terraform has not been
  # started, or has been started and has not emitted a resource. It is not a
  # failure and it publishes nothing - a document saying every node is waiting
  # is indistinguishable from one written before the apply began.
  if compgen -G "${TF_STREAM_DIR}/*.jsonl" > /dev/null 2>&1; then
    if python3 scripts/fold-timeline.py \
         --environment "$env_name" \
         --stream-dir "$TF_STREAM_DIR" \
         --out "${work}/timeline.json" > /dev/null 2>&1 &&
       python3 scripts/node-states.py \
         --topology "$topology" \
         --timeline "${work}/timeline.json" \
         --out "${work}/nodes.json" --quiet > /dev/null 2>&1 &&
       scripts/publish-progress.sh "$env_name" "${work}/nodes.json" > /dev/null 2>&1
    then
      published=$((published + 1))
    else
      failed=$((failed + 1))
    fi
  fi

  nap || break
done

rm -rf "$work"
echo "watch-progress: ${published} reading(s) published, ${failed} failed"

# ALWAYS ZERO. Said out loud because a non-zero status here would fail a job
# whose apply succeeded, over an instrument.
exit 0
