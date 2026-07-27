#!/usr/bin/env bash
# Publish one environment's observed state, and optionally its Playwright
# report, to the public dashboard bucket. Then invalidate exactly what changed.
#
# Runs under the NARROW PUBLISH ROLE (infra/public-site), not the deploy role:
# s3:PutObject/DeleteObject on this bucket, cloudfront:CreateInvalidation on
# this distribution, and nothing else. The split is deliberate - the credential
# that can change infrastructure is not the credential that writes the page
# reporting on it. It also means this script cannot read AWS state itself, which
# is why the observation arrives as a file from scripts/observe-environment.sh.
#
# Objects written:
#   status/<environment>.json                          the state panel's source
#   reports/<environment>/<run id>/                     immutable evidence
#   reports/<environment>/latest/                       a link that stays valid
#
# ONE FILE PER ENVIRONMENT, not the single status.json ADR-0026 describes. Two
# workflows can be in flight at once - destroying prod while stage deploys is a
# normal cycle here - and a shared file would need read-modify-write against S3,
# which has no compare-and-set. Two independent keys have no race to lose. The
# page reads both; the ADR's rule that a source may only assert what it observes
# is untouched, and in fact sharpened: each file has exactly one writer.
#
# Usage:
#   scripts/publish-status.sh <environment> <observation-json> [report-dir]
#
# Environment:
#   SITE_BUCKET           required
#   SITE_DISTRIBUTION_ID  required
#   SITE_BASE_URL         optional, defaults to https://demo.uveapp.net
#   JOB_STATUS            required. GitHub's ${{ job.status }} at the moment
#                         this step runs - the workflow's own observation about
#                         itself, and the only thing it is entitled to assert.
set -euo pipefail

env_name="${1:?usage: publish-status.sh <environment> <observation-json> [report-dir]}"
observation="${2:?missing observation JSON produced by observe-environment.sh}"
report_dir="${3:-}"

: "${SITE_BUCKET:?SITE_BUCKET is not set}"
: "${SITE_DISTRIBUTION_ID:?SITE_DISTRIBUTION_ID is not set}"
: "${JOB_STATUS:?JOB_STATUS is not set}"
base_url="${SITE_BASE_URL:-https://demo.uveapp.net}"

run_id="${GITHUB_RUN_ID:-local}"
report_url='null'
invalidate=("/status/${env_name}.json")

# ---- the report, if this workflow produced one -----------------------------
# GitHub Actions artifacts require a logged-in GitHub account to download, so
# today's report is evidence only for people who already have access. Publishing
# it is what turns a green tick into something an outside reader can check.
if [ -n "$report_dir" ] && [ -d "$report_dir" ] && [ -n "$(ls -A "$report_dir" 2>/dev/null)" ]; then
  for dest in "$run_id" latest; do
    aws s3 sync "$report_dir" "s3://${SITE_BUCKET}/reports/${env_name}/${dest}/" \
      --delete --only-show-errors
  done
  report_url="\"${base_url}/reports/${env_name}/${run_id}/index.html\""
  invalidate+=("/reports/${env_name}/latest/*")
  echo "published report: ${base_url}/reports/${env_name}/${run_id}/index.html"
else
  echo "no report directory to publish (looked at: '${report_dir:-<none>}')"
fi

# ---- the run block ---------------------------------------------------------
# Added here rather than in the observation, because these are facts about the
# WORKFLOW and the observation is only allowed to talk about AWS. The run id is
# also the staleness detector: the page compares it against the newest run the
# GitHub API reports, and renders "unknown" rather than a stale value when the
# newest run is younger than this file (ADR-0026).
status_json="$(jq \
  --arg run_id "$run_id" \
  --arg run_number "${GITHUB_RUN_NUMBER:-}" \
  --arg run_attempt "${GITHUB_RUN_ATTEMPT:-}" \
  --arg workflow "${GITHUB_WORKFLOW:-}" \
  --arg job_status "$JOB_STATUS" \
  --arg url "${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-UVE-QA/aws-devops-sdet-demo}/actions/runs/${run_id}" \
  --arg written_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson report_url "$report_url" \
  '. + {
     report_url: $report_url,
     written_at: $written_at,
     run: {
       id: $run_id,
       number: $run_number,
       attempt: $run_attempt,
       workflow: $workflow,
       status: $job_status,
       url: $url
     }
   }' "$observation")"

printf '%s\n' "$status_json" > /tmp/status-"${env_name}".json
echo "::group::status/${env_name}.json"
printf '%s\n' "$status_json"
echo "::endgroup::"

# no-cache so a viewer who reloads gets the truth even if an invalidation is
# still propagating. The HTML is cached normally; this file is the volatile one.
aws s3 cp /tmp/status-"${env_name}".json "s3://${SITE_BUCKET}/status/${env_name}.json" \
  --content-type application/json \
  --cache-control "no-cache, max-age=0" \
  --only-show-errors

id="$(aws cloudfront create-invalidation \
  --distribution-id "$SITE_DISTRIBUTION_ID" \
  --paths "${invalidate[@]}" \
  --query 'Invalidation.Id' --output text)"
echo "invalidation $id for: ${invalidate[*]}"
