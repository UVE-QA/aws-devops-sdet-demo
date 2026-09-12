#!/usr/bin/env bash
# Publish ONE partial reading of a cycle that is still running (ADR-0076).
#
#   status/progress/<environment>.json
#
# The document is the same join scripts/node-states.py writes at the end of a
# job, taken from the SAME streams while terraform is still writing them. Nothing
# in the fold or the join changes to produce it: a stream with no `.rc` beside it
# already folds to `incomplete`, and a node whose members have not all finished
# already comes out `incomplete` with `resources_complete` under
# `resources_observed`. That is not a weakened reading of a finished cycle - it
# is an accurate reading of an unfinished one, and it is exactly the three states
# a board needs:
#
#   the node is absent from the document   nothing of it has started
#   incomplete, 3 of 8 complete            it is being created, and 3 are done
#   measured                               every member of it finished
#
# WHY THIS IS NOT publish-status.sh. That script publishes the RECORD of a cycle:
# it takes an observation of AWS, a job status, a report, a cost fold, and it
# ends with a CloudFront invalidation. Running it every fifteen seconds would
# mean thirty invalidations per apply, which is a billed request past the monthly
# allowance and a queue with a documented limit - to republish a document that
# says `no-cache` and is revalidated at the edge anyway.
#
# So this writes one object and invalidates nothing. It is under `status/`
# deliberately and not under a prefix of its own: publish-site.sh already
# excludes `status/*` from its `--delete` sync, so ADR-0044's correspondence -
# the one that once deleted a cycle's folded results from a bucket with no
# versioning - is satisfied without a new line anybody has to remember. The
# checker reads every publisher in this directory now rather than one by name.
#
# THE DOCUMENT SAYS WHAT IT IS. A partial reading published under the same shape
# as a final one would be indistinguishable from the record, and the page would
# have no way to know it is watching a cycle rather than reporting on one. The
# envelope carries `partial: true`, the run that is producing it, and the moment
# it was taken.
#
# Usage:
#   scripts/publish-progress.sh <environment> <nodes-json>
#
# Environment:
#   SITE_BUCKET  required
#   GITHUB_RUN_ID, GITHUB_RUN_NUMBER, GITHUB_WORKFLOW  optional; when present
#                 they name the run this reading belongs to, which is what lets
#                 the page tell a cycle under way from a document left behind by
#                 one that is over.
set -euo pipefail

env_name="${1:?usage: publish-progress.sh <environment> <nodes-json>}"
nodes_json="${2:?usage: publish-progress.sh <environment> <nodes-json>}"

: "${SITE_BUCKET:?SITE_BUCKET is not set}"

case "$env_name" in
  stage|prod) ;;
  *) echo "publish-progress: unknown environment '$env_name'" >&2; exit 2 ;;
esac

[ -s "$nodes_json" ] || { echo "publish-progress: $nodes_json is missing or empty" >&2; exit 2; }

out="$(mktemp)"
python3 - "$env_name" "$nodes_json" > "$out" <<'PY'
import json, os, sys, datetime

env_name, nodes_path = sys.argv[1], sys.argv[2]
nodes = json.load(open(nodes_path))

# The join's own output, wrapped rather than rewritten. Rewriting it here would
# be a second opinion about what a node state is, held in a shell script, and
# this repository has paid twice for one definition on two hosts.
print(json.dumps({
    "_": "A PARTIAL reading of a cycle still in flight (ADR-0076). Written by "
         "scripts/publish-progress.sh from the same fold and the same join that "
         "produce the record at the end of the job, over streams terraform has "
         "not finished writing. Not a record: it is replaced every few seconds "
         "and removed when the job ends. `incomplete` here means IN PROGRESS, "
         "which is the same thing it means in a killed run - the difference is "
         "that this document says a run is producing it.",
    "partial": True,
    "environment": env_name,
    "taken_at": datetime.datetime.now(datetime.timezone.utc)
                 .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "run": {
        "id": os.environ.get("GITHUB_RUN_ID") or None,
        "number": os.environ.get("GITHUB_RUN_NUMBER") or None,
        "workflow": os.environ.get("GITHUB_WORKFLOW") or None,
    },
    # WHICH DIRECTION THIS CYCLE IS GOING. node-states.py already decides it
    # from the operations in the timeline, and the page needs it: the same
    # `incomplete` node means `being created` under an apply and `being removed`
    # under a destroy, and a board that said `creating` through a teardown would
    # be confidently backwards.
    "kind": nodes.get("kind"),
    "observed": nodes.get("observed"),
    "nodes": nodes.get("nodes", {}),
    # THE BOARD GOING DARK, ONE NOUN AT A TIME (ADR-0090). `nodes` under a
    # destroy holds ONE entry - the whole level - because that is what a delete
    # is matched by; this is the same deletes read a second way, by address, so
    # the estate tiles can go out as they go rather than all at once. `None`
    # under an apply, where the join produces none.
    "deleting": nodes.get("deleting"),
    "unmatched": nodes.get("unmatched"),
}, indent=2))
PY

# `no-cache` and no invalidation. The header makes every edge request revalidate
# against the origin, which is what a document replaced every fifteen seconds
# needs; an invalidation is for a document that is replaced rarely and must be
# gone from the edge NOW. ADR-0065 is the reason the header is set explicitly
# rather than left to CloudFront's heuristic - the page whose whole argument is
# that state should be observed had no cache policy at all until it was.
aws s3 cp "$out" "s3://${SITE_BUCKET}/status/progress/${env_name}.json" \
  --content-type application/json \
  --cache-control "no-cache, max-age=0" \
  --only-show-errors
rm -f "$out"
