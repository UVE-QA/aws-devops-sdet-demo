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

# --cache-control IS THE SECOND LOAD-BEARING FLAG (ADR-0065). Without it these
# objects go to S3 with no freshness policy at all, and a browser holding an old
# copy then applies HEURISTIC caching - roughly a tenth of the document's age -
# so a page last published three weeks ago can be served from a visitor's cache
# for days after a new one is live. The CloudFront invalidation below does not
# reach that copy; it only fixes the edge.
#
# Observed, not reasoned about: on 2026-09-05 a fresh tab rendered the previous
# page while `curl` on the same URL at the same moment returned the new one.
#
# `no-cache` does NOT mean "do not cache". It means revalidate before use, which
# with the ETag S3 already sends is a conditional request and a 304 - the same
# policy scripts/publish-status.sh has always set on the documents the CYCLE
# writes. The page's own HTML was the one document making the "observed, not
# assumed" claim while having no policy about its own freshness.
#
# It covers index.html AND data/, deliberately. The page renders counts out of
# data/topology.json, so an index.html that revalidates beside a topology.json
# that does not is two documents free to disagree about the same page.
aws s3 sync "$src" "s3://${SITE_BUCKET}/" \
  --delete \
  --cache-control "no-cache" \
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
