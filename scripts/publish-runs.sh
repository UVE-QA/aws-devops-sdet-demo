#!/usr/bin/env bash
# THE RUN HISTORY IS THE BUCKET'S (ADR-0100). The page used to read the GitHub
# Actions API anonymously from the visitor's browser: 60 requests an hour per
# IP address, shared by every tab and every site that IP reads GitHub from -
# and on 2026-09-14 the owner's browser, with this dashboard and the
# zero-trust-lab one open, met HTTP 403 before its first successful read.
#
# So the cycle publishes its own history. This writes status/runs.json - the
# forty newest runs of the repository, the forty newest of the released line,
# and the jobs and steps of one run - taken with the runner's token (1000
# requests an hour for the repository, none of them the visitor's) and put
# beside the status documents the page already trusts. Called by the progress
# watcher every minute while a job runs, by publish-status.sh when a job ends,
# and by publish-runs.yml when a workflow completes - the one moment no job of
# the run can see, because the run is not complete until its last job is.
#
#   scripts/publish-runs.sh <reason> [--run-id ID]
#
#   reason      watcher | job-end | completed - recorded in the document
#   --run-id    whose jobs to include; defaults to GITHUB_RUN_ID
#
# Needs GH_TOKEN (the workflow's github.token, with actions: read), SITE_BUCKET,
# GITHUB_REPOSITORY, and AWS credentials that may write status/ in the bucket
# (the site-publish role). Fails LOUDLY on a bad read and writes nothing: a
# snapshot with half a history is worse than the last good one.
set -euo pipefail

reason="${1:?usage: publish-runs.sh <reason> [--run-id ID]}"
shift
run_id="${GITHUB_RUN_ID:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) run_id="$2"; shift 2 ;;
    *) echo "publish-runs: unknown argument $1" >&2; exit 2 ;;
  esac
done
: "${GH_TOKEN:?GH_TOKEN is not set - the workflow token github.token, with actions: read}"
[ -n "${PUBLISH_RUNS_OUT:-}" ] || : "${SITE_BUCKET:?SITE_BUCKET is not set}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}"
released="${RELEASED_BRANCH:-main}"
per_page="${RUNS_PER_PAGE:-40}"

# The fields the page reads and nothing else, so the document stays small
# (a raw run is ~5 KB, forty of them twice over is 400 KB; trimmed, ~30 KB).
run_fields='{id, run_number, name, display_title, path, event, status, conclusion,
             head_branch, head_sha, created_at, updated_at, run_started_at, run_attempt, html_url}'
job_fields='[.jobs[] | {id, name, status, conclusion, started_at, completed_at, html_url,
             steps: [(.steps // [])[] | {number, name, status, conclusion, started_at, completed_at}]}]'

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

gh api "repos/${GITHUB_REPOSITORY}/actions/runs?per_page=${per_page}" \
  --jq "[.workflow_runs[] | ${run_fields}]" > "${work}/all.json"
gh api "repos/${GITHUB_REPOSITORY}/actions/runs?branch=${released}&per_page=${per_page}" \
  --jq "[.workflow_runs[] | ${run_fields}]" > "${work}/released.json"
if [ -n "$run_id" ]; then
  gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${run_id}/jobs?per_page=100" \
    --jq "${job_fields}" > "${work}/jobs.json"
  run_status="$(jq -r --argjson id "$run_id" '(map(select(.id == $id)) | .[0].status) // "unknown"' "${work}/all.json")"
else
  echo "[]" > "${work}/jobs.json"
  run_status="null"
fi

jq -n \
  --arg reason "$reason" \
  --arg released "$released" \
  --arg written_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg run_id "${GITHUB_RUN_ID:-}" \
  --arg run_number "${GITHUB_RUN_NUMBER:-}" \
  --arg workflow "${GITHUB_WORKFLOW:-}" \
  --arg job "${GITHUB_JOB:-}" \
  --arg jobs_run "$run_id" \
  --arg run_status "$run_status" \
  --slurpfile all "${work}/all.json" \
  --slurpfile rel "${work}/released.json" \
  --slurpfile jobs "${work}/jobs.json" \
  '{
    schema: 1,
    "_": "The run history, written by the cycle itself (ADR-0100). The page reads this instead of the GitHub API - anonymous GitHub is 60 requests an hour per IP, shared by every tab - and asks GitHub only when this document is missing. Replaced every minute while a job runs, when a job ends, and when a workflow completes.",
    written_at: $written_at,
    reason: $reason,
    written_by: { run_id: $run_id, run_number: $run_number, workflow: $workflow, job: $job },
    released_branch: $released,
    all_runs: $all[0],
    released_runs: ($rel[0] | map(select(.head_branch == $released))),
    jobs: { run_id: ($jobs_run | if . == "" then null else tonumber end),
            status: (if $run_status == "null" then null else $run_status end),
            jobs: $jobs[0] }
  }' > "${work}/runs.json"

# PUBLISH_RUNS_OUT: write the document to a local path instead of the bucket
# - how the page's fixtures are taken from the real API rather than typed.
if [ -n "${PUBLISH_RUNS_OUT:-}" ]; then
  cp "${work}/runs.json" "$PUBLISH_RUNS_OUT"
else
  aws s3 cp "${work}/runs.json" "s3://${SITE_BUCKET}/status/runs.json" \
    --content-type application/json \
    --cache-control "no-cache, max-age=0" \
    --only-show-errors
fi
echo "publish-runs: ${reason} - $(jq -r '.all_runs | length' "${work}/runs.json") runs, " \
  "$(jq -r '.released_runs | length' "${work}/runs.json") of ${released}, " \
  "$(jq -r '.jobs.jobs | length' "${work}/runs.json") job(s) of ${run_id:-none}"
