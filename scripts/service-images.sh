#!/usr/bin/env bash
# THE SERVICES' IMAGES, FROM THE MANIFEST (ADR-0101 D6). Every workflow that
# needed a repository URL or a digest per service used to spell the three
# repository names itself - fifteen copies across four files by the end of
# item 4. This is the one place that turns services.json into what a
# workflow needs, and it prints JSON keyed by service name so a caller loops
# with jq instead of naming anyone.
#
#   scripts/service-images.sh repos                  {name: url}
#   scripts/service-images.sh tag <tag>              {name: url@digest}  the tag must be in every repository
#   scripts/service-images.sh digests <json>         {name: url@digest}  <json> is {name: digest}, e.g. the rollback pointer;
#                                                                        every digest must still exist in its repository
#
# With `--output <prefix>` and GITHUB_OUTPUT set, it also writes one step
# output per service - `<prefix>_<name>=<value>` - and `<prefix>s=<json>`
# with the whole object, so an expression can name one service
# (`steps.image.outputs.ref_api`) and a script can loop over all of them.
#
# Refusals are `::error::` lines and exit 1, actionable the way the inline
# copies were: a missing repository says which level to apply, a missing tag
# says which run should have pushed it, a missing digest says the lifecycle
# policy expired it. Needs AWS_REGION and credentials that may read ECR.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/services.json"
: "${AWS_REGION:?AWS_REGION is not set}"

mode="${1:?mode: repos | tag <tag> | digests <json>}"
shift
arg=""
prefix=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) prefix="${2:?--output needs a prefix}"; shift 2 ;;
    *) arg="$1"; shift ;;
  esac
done

repo_url() {  # repo_url <repository> -> url
  local url
  url="$(aws ecr describe-repositories --region "$AWS_REGION" \
           --repository-names "$1" \
           --query 'repositories[0].repositoryUri' --output text 2>/dev/null || true)"
  if [ -z "$url" ] || [ "$url" = "None" ]; then
    echo "::error::shared ECR repository $1 not found - apply infra/shared-ecr first (ADR-0018, ADR-0095)" >&2
    exit 1
  fi
  echo "$url"
}

digest_of_tag() {  # digest_of_tag <repository> <tag> -> digest
  local digest
  digest="$(aws ecr describe-images --region "$AWS_REGION" \
              --repository-name "$1" --image-ids imageTag="$2" \
              --query 'imageDetails[0].imageDigest' --output text 2>/dev/null || true)"
  if [ -z "$digest" ] || [ "$digest" = "None" ]; then
    echo "::error::tag '$2' is not in $1 - promote a tag that a green deploy-stage run pushed" >&2
    exit 1
  fi
  echo "$digest"
}

digest_exists() {  # digest_exists <repository> <digest>
  if ! aws ecr describe-images --region "$AWS_REGION" \
         --repository-name "$1" --image-ids imageDigest="$2" >/dev/null 2>&1; then
    echo "::error::rollback target $2 is no longer in $1 - the lifecycle policy expired it. prod is left standing for inspection." >&2
    exit 1
  fi
}

result="{}"
while IFS=$'\t' read -r name image; do
  url="$(repo_url "$image")"
  case "$mode" in
    repos)
      value="$url" ;;
    tag)
      value="$url@$(digest_of_tag "$image" "${arg:?tag}")" ;;
    digests)
      digest="$(jq -r --arg n "$name" '.[$n] // empty' <<<"${arg:?json of digests}")"
      if [ -z "$digest" ] || [ "$digest" = "none" ]; then
        echo "::error::no digest for $name in $arg - a release is every service in services.json or nothing" >&2
        exit 1
      fi
      digest_exists "$image" "$digest"
      value="$url@$digest" ;;
    *)
      echo "::error::unknown mode $mode" >&2; exit 1 ;;
  esac
  result="$(jq -c --arg n "$name" --arg v "$value" '. + {($n): $v}' <<<"$result")"
done < <(jq -r '.services[] | [.name, .image] | @tsv' "$MANIFEST")

if [ "$(jq 'length' <<<"$result")" -eq 0 ]; then
  echo "::error::services.json declares no services" >&2
  exit 1
fi

if [ -n "$prefix" ] && [ -n "${GITHUB_OUTPUT:-}" ]; then
  {
    echo "${prefix}s=$result"
    jq -r --arg p "$prefix" 'to_entries[] | "\($p)_\(.key)=\(.value)"' <<<"$result"
  } >> "$GITHUB_OUTPUT"
fi
echo "$result"
