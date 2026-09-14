#!/usr/bin/env bash
# ONE IMAGE, BUILT AND PUSHED - WITH A SECOND AND A THIRD TRY. The public
# launch #34 (2026-09-14, the first from the button after ADR-0100) failed in
# two seconds on `failed to fetch oauth token: Post https://auth.docker.io/
# token: connection reset by peer` - the runner could not reach Docker Hub for
# the base image's metadata, once. Six copies of the same twelve lines in two
# workflows had no second try. This is the one copy, and it tries three times
# with a pause between, because a reset connection is weather and not a
# verdict; a build that fails three times in a row is a verdict and fails.
#
#   scripts/build-and-push-image.sh <ecr_url> <repository> <tag> <context>
#
# The registry is IMMUTABLE (ADR-0029), so an existing tag is reused rather
# than rebuilt. On the public path that is also the common case: every launch
# runs the same commit. Needs AWS_REGION and a docker login to the registry.
set -euo pipefail
ecr_url="${1:?ecr url}"
repository="${2:?repository name}"
tag="${3:?image tag}"
context="${4:?build context}"
: "${AWS_REGION:?AWS_REGION is not set}"

if aws ecr describe-images --region "$AWS_REGION" \
     --repository-name "$repository" \
     --image-ids imageTag="$tag" >/dev/null 2>&1; then
  echo "$tag is already in $repository - reusing it, not rebuilding"
  exit 0
fi

attempts="${BUILD_ATTEMPTS:-3}"
for attempt in $(seq 1 "$attempts"); do
  if docker build -t "${ecr_url}:${tag}" "$context" && docker push "${ecr_url}:${tag}"; then
    echo "built and pushed ${repository}:${tag} on attempt ${attempt}"
    exit 0
  fi
  if [ "$attempt" -lt "$attempts" ]; then
    pause=$((attempt * 20))
    echo "attempt ${attempt} of ${attempts} failed for ${repository}; trying again in ${pause}s" >&2
    sleep "$pause"
  fi
done
echo "build-and-push-image: ${repository}:${tag} failed ${attempts} times; that is a verdict, not weather" >&2
exit 1
