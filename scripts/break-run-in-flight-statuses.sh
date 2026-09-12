#!/usr/bin/env bash
# BREAK TEST for "a run is in flight until it is completed" (Phase 40, ADR-0086 D1).
#
#     bash scripts/break-run-in-flight-statuses.sh
#
# GitHub gives a run more statuses than the two the page used to name. Between
# one job of a cycle ending and the next leaving the queue the run is `queued`,
# and `figuresAreOlder()` called that *not in flight* - so for most of a 148 s
# read window the map dropped every qualifier it had and the text above it dated
# the running cycle as the last one that finished. Four such gaps per cycle.
#
# The fixture holds ONE moment and the run in it is `in_progress`, so the defect
# cannot be reached from it. This moves the run through the statuses a real cycle
# actually has and asserts the page says the same thing about all of them:
#
#   [B] queued     - between two jobs of one cycle. The one that was wrong
#   [C] waiting    - held at an environment gate
#   [D] requested  - a status this page has never seen and may not assume about
#   [E] the predicate put back the way it was, with the run `queued`: seven stage
#       nodes print the previous cycle's figures with nothing saying so, which is
#       what the page did on 2026-09-11 at 20:09
#
# The fixture and the template are restored with `git checkout`, so both must be
# clean before this runs. CHROMIUM_PATH= as for the gate itself.

set -uo pipefail
cd "$(dirname "$0")/.."

TPL="assets/index.template.html"
RUNS="tests/fixtures/page-inflight/in-flight/runs.json"
GATE="scripts/check-page-inflight.mjs"
OUT="$(mktemp -d)/gate.out"
pass=0
fail=0

if [ -n "$(git status --porcelain -- "$TPL" "$RUNS" "$GATE")" ]; then
  echo "break-run-in-flight-statuses: the template, the fixture or the gate is dirty."
  echo "Commit first - every variant restores them with git checkout, which would take"
  echo "your edit with it."
  exit 2
fi

restore() {
  git checkout -- "$TPL" "$RUNS" "$GATE" 2>/dev/null
  python3 scripts/build-site-page.py > /dev/null 2>&1
}
trap restore EXIT

set_status() {  # set_status <status>
  STATUS="$1" python3 - <<'PY'
import json, os
p = "tests/fixtures/page-inflight/in-flight/runs.json"
d = json.load(open(p))
runs = d["workflow_runs"] if isinstance(d, dict) and "workflow_runs" in d else d
hit = 0
for r in runs:
    if r.get("id") == 31461000064:
        r["status"] = os.environ["STATUS"]
        hit += 1
assert hit == 1, "the run the fixture calls in flight is not there; this variant would prove nothing"
json.dump(d, open(p, "w"), indent=2)
PY
}

run_gate() {
  python3 scripts/build-site-page.py > /dev/null 2>&1
  node "$GATE" > "$OUT" 2>&1
  echo $?
}

check() {  # check <label> <expected exit> <expected regex>
  local label="$1" want_exit="$2" want="$3" got_exit line
  got_exit="$(run_gate)"
  line="$(grep -E 'in-flight: a figure|does not say so|page-inflight:' "$OUT" | head -4)"
  # `nonzero` rather than a number, for the one variant that breaks the page:
  # the gate answers 1 for a claim that did not hold and 2 when it refuses to
  # judge at all, and a mutation this large earns both at once. Pinning the digit
  # would make this variant pass or fail on which complaint arrived first.
  if { [ "$want_exit" = "nonzero" ] && [ "$got_exit" != "0" ] || [ "$got_exit" = "$want_exit" ]; } \
     && grep -qE "$want" "$OUT"; then
    printf 'ok    %s\n' "$label"
    pass=$((pass + 1))
  else
    printf 'FAIL  %s\n' "$label"
    printf '      wanted exit %s matching: %s\n' "$want_exit" "$want"
    printf '      got exit %s\n' "$got_exit"
    fail=$((fail + 1))
  fi
  printf '%s\n\n' "$line" | sed 's/^/        /'
}

echo "=== [A] control: the fixture as committed, in_progress ==="
check "every claim holds" 0 'page-inflight: every claim held'

echo "=== [B] the same run, queued: between two jobs of one cycle ==="
set_status queued
check "a queued run is still a run in flight" 0 'page-inflight: every claim held'
restore

echo "=== [C] the same run, waiting ==="
set_status waiting
check "a waiting run is still a run in flight" 0 'page-inflight: every claim held'
restore

echo "=== [D] the same run, requested: a status this page has never seen ==="
set_status requested
check "an unfamiliar status is not read as finished" 0 'page-inflight: every claim held'
restore

echo "=== [E] the old predicate, with the run queued: the defect itself ==="
# Both halves, because the page asks the same question in two places and the
# defect needed only one of them. This is the pair as they stood on 2026-09-11.
set_status queued
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = "          return observation.run.status !== \"completed\";"
new = "          const s = observation.run.status;\n          return s === \"in_progress\" || s === \"waiting\";"
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
s = s.replace(old, new)
old2 = "          if (run.status === \"completed\") return none;"
new2 = "          if (run.status !== \"in_progress\" && run.status !== \"waiting\") return none;"
assert s.count(old2) == 1, "the second anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old2, new2))
PY
check "the two-status predicate drops every qualifier at once" nonzero \
      'prints a figure from the cycle before this one and does not say so'
restore

echo "=== [F] control again, after every mutation was restored ==="
check "the control is green on both sides of the breaks" 0 'page-inflight: every claim held'

printf 'break-run-in-flight-statuses: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
