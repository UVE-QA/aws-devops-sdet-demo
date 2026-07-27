#!/usr/bin/env bash
# Publish the static dashboard (site/) to the public bucket and invalidate it.
#
# Runs under the narrow publish role, same as scripts/publish-status.sh.
#
# THE --exclude LINES ARE THE POINT. `aws s3 sync --delete` would otherwise
# remove every object the lifecycle workflows wrote: the environment status
# files and every published Playwright report. A "publish the site" step that
# deletes the evidence the site exists to show is precisely this project's
# recurring failure mode - a command doing something its name denies - so the
# exclusions are load-bearing, not tidiness.
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
  --only-show-errors

echo "::group::bucket contents"
aws s3 ls "s3://${SITE_BUCKET}/" --recursive --human-readable
echo "::endgroup::"

id="$(aws cloudfront create-invalidation \
  --distribution-id "$SITE_DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' --output text)"
echo "invalidation $id for /*"
