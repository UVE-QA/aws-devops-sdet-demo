#!/usr/bin/env bash
# BREAK TEST for the phase-span merge (Phase 39, ADR-0083).
#
#     bash scripts/break-phase-span-merge.sh
#
# A phase that runs as two jobs publishes two spans under one key, one per
# environment document. readRunLayer() kept whichever was folded last, which is
# `ENVS` order and nothing else - so phase 8's at-rest figure was one of its two
# teardowns, chosen by an array literal, while the live clock beside it ran from
# the first bound step to now. Two numbers that had never measured the same
# thing.
#
# Three variants, and the third is the point:
#
#   [B] both documents name ONE run - the self-service shape - and the figure
#       must be their UNION, not either one
#   [C] the same fixture with the merge taken out of the page: the figure falls
#       back to one job's span, which is what shows the merge did it
#   [A]/[D] the tree as committed, where the two documents name DIFFERENT runs -
#       the owner's path, two dispatches of destroy.yml, not one cycle - and the
#       figure must stay ONE of them
#
# The fixture and the template are restored with `git checkout`, so both must be
# clean before this runs.

set -uo pipefail
cd "$(dirname "$0")/.."

TPL="assets/index.template.html"
STAGE_DOC="tests/fixtures/page-inflight/layer/timeline/stage/nodes-destroy.json"
PROD_DOC="tests/fixtures/page-inflight/layer/timeline/prod/nodes-destroy.json"
pass=0
fail=0

if [ -n "$(git status --porcelain -- "$TPL" "$STAGE_DOC" "$PROD_DOC")" ]; then
  echo "break-phase-span-merge: the template or the fixture is dirty. Commit first -"
  echo "every variant restores them with git checkout, which would take your edit with it."
  exit 2
fi

restore() {
  git checkout -- "$TPL" "$STAGE_DOC" "$PROD_DOC" 2>/dev/null
  python3 scripts/build-site-page.py > /dev/null 2>&1
}
trap restore EXIT

read_span() {
  python3 scripts/build-site-page.py > /dev/null 2>&1
  node scripts/read-phase-span.mjs "Destroy" 2>&1 | head -1
}

check() {  # check <label> <expected substring>
  local label="$1" want="$2" got
  got="$(read_span)"
  if printf '%s' "$got" | grep -qF "$want"; then
    printf 'ok    %s\n        %s\n' "$label" "$got"
    pass=$((pass + 1))
  else
    printf 'FAIL  %s\n        wanted to contain: %s\n        got: %s\n' "$label" "$want" "$got"
    fail=$((fail + 1))
  fi
}

# stage 19:20:12 -> 19:31:30 (678s), prod 19:40:15 -> 19:52:20 (725s).
# Union of the two: 19:20:12 -> 19:52:20 = 1928s = 32m 8s.
one_cycle() {
  python3 - <<'PY'
import json
for p in ("tests/fixtures/page-inflight/layer/timeline/stage/nodes-destroy.json",
          "tests/fixtures/page-inflight/layer/timeline/prod/nodes-destroy.json"):
    d = json.load(open(p))
    d["cycle"]["run"]["id"] = 31457000045          # one cycle tore both down
    json.dump(d, open(p, "w"), indent=2)
PY
}

echo "=== [A] as committed: two dispatches, two runs, one of them wins ==="
check "the figure is one teardown's span" "12m 5s"

echo "=== [B] one cycle tore both down: the figure is their union ==="
one_cycle
check "stage 11m 18s + a wait + prod 12m 5s reads as 32m 8s" "32m 8s"

echo "=== [C] same fixture, merge removed: it falls back to one job ==="
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = "                  const sameRun = had.run && span.run && had.run === span.run;"
new = "                  const sameRun = false;"
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "without the merge the union is not drawn" "12m 5s"
restore

echo "=== [D] control: restored, and back to one of the two ==="
check "the committed tree draws one teardown's span again" "12m 5s"

printf 'break-phase-span-merge: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
