#!/usr/bin/env bash
# ONE SERVICE, BUILT BY NAME (ADR-0101 D6). The workflow step says which
# service; the manifest says its repository and its build context; the
# registry says the URL. Before this the step carried all three itself, six
# times over two workflows.
#
#   scripts/build-service.sh <name> <tag>
#
# The build and the push, with their three tries and the immutable-registry
# reuse, stay in scripts/build-and-push-image.sh. Needs AWS_REGION and a
# docker login to the registry.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:?service name, as services.json declares it}"
tag="${2:?image tag}"

read -r image context < <(jq -r --arg n "$name" \
  '.services[] | select(.name == $n) | [.image, .context] | @tsv' "$ROOT/services.json" | tr '\t' ' ')
if [ -z "${image:-}" ] || [ -z "${context:-}" ]; then
  echo "::error::services.json declares no service named $name" >&2
  exit 1
fi
url="$("$ROOT/scripts/service-images.sh" repos | jq -r --arg n "$name" '.[$n]')"
exec "$ROOT/scripts/build-and-push-image.sh" "$url" "$image" "$tag" "$ROOT/$context"
