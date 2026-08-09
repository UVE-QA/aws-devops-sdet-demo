#!/usr/bin/env bash
# Publish the static dashboard (site/) to the public bucket and invalidate it.
#
# Runs under the narrow publish role, same as scripts/publish-status.sh.
#
# THE --exclude LINES ARE THE POINT. `aws s3 sync --delete` would otherwise
# remove every object the lifecycle workflows wrote: the environment status
# files, every published Playwright report, and every timeline. A "publish the
# site" step that deletes the evidence the site exists to show is precisely this
# project's recurring failure mode - a command doing something its name denies -
# so the exclusions are load-bearing, not tidiness.
#
# ONE PREFIX PER THING THE LIFECYCLE WRITES, and adding a prefix means adding a
# line here in the same commit. timeline/ was the third, and the cost of
# forgetting it would have been silent: the map would keep working from the
# timeline published minutes earlier and lose it at the next push to main.
#
# THE FOURTH IS WHY THAT SENTENCE IS NOW A CHECK. ADR-0042 added results/ to
# publish-status.sh on 2026-08-08 and nothing added the line below. Nothing went
# wrong for the rest of that day, because no push to main touched site/ - and
# the push that finally did was the one publishing the page that READS those
# results. It deleted every one of them. The bucket has no versioning: the
# folded test results of cycle 31276975666 do not exist any more.
#
# `make publish-prefixes-check` now reads the prefixes out of publish-status.sh
# and refuses if any is missing here (ADR-0044). Keep both - the comment says
# why, the check says whether.
#
# Usage:
#   scripts/publish-site.sh [source-dir]
#
# Environment:
#   SITE_BUCKET           required
#   SITE_DISTRIBUTION_ID  required
set -euo pipefail

src="${1:-site}"
: "${SITE_BUCKET:?SITE_BUCKET is not set}"
: "${SITE_DISTRIBUTION_ID:?SITE_DISTRIBUTION_ID is not set}"
[ -d "$src" ] || { echo "::error::source directory '$src' does not exist"; exit 1; }

aws s3 sync "$src" "s3://${SITE_BUCKET}/" \
  --delete \
  --exclude "status/*" \
  --exclude "reports/*" \
  --exclude "timeline/*" \
  --exclude "results/*" \
  --exclude "cost/*" \
  --only-show-errors

echo "::group::bucket contents"
aws s3 ls "s3://${SITE_BUCKET}/" --recursive --human-readable
echo "::endgroup::"

id="$(aws cloudfront create-invalidation \
  --distribution-id "$SITE_DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' --output text)"
echo "invalidation $id for /*"
