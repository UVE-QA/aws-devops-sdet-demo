#!/usr/bin/env bash
# BREAK TEST for the sequence half of page-inflight-check (Phase 29).
#
# Claims 4 and 5 exist because ADR-0062's two findings cannot be held still: one
# lives in the run layer changing underneath an open page, the other in the clock
# running while the API's answer changes. A gate over a moving subject is exactly
# the kind that can look green forever, so each break below reintroduces one
# defect INTO THE PAGE, rebuilds, and requires the gate to say so.
#
#     bash scripts/break-page-inflight-sequence.sh
#
# The tree must be clean: every variant patches assets/index.template.html and
# restores it with `git checkout`, which discards anything uncommitted in it.
# That has cost this project a completed edit once already (2026-07-28).
#
# CHROMIUM_PATH= as for the gate itself.

set -uo pipefail
cd "$(dirname "$0")/.."

TPL="assets/index.template.html"
GATE="scripts/check-page-inflight.mjs"
OUT="$(mktemp -d)/gate.out"
pass=0
fail=0

if [ -n "$(git status --porcelain -- "$TPL" "$GATE")" ]; then
  echo "break-page-inflight-sequence: $TPL or $GATE is dirty. Commit first - every"
  echo "variant below restores them with git checkout, which would take your edit with it."
  exit 2
fi

restore() {
  git checkout -- "$TPL" "$GATE" 2>/dev/null
  python3 scripts/build-site-page.py > /dev/null 2>&1
}
trap restore EXIT

# The gate's exit status, taken from the gate and not through a pipe: `$?` after
# a pipe is the pipe's, which read as a gate that would not break once here
# already (Phase 15b, Checkov).
run_gate() {
  python3 scripts/build-site-page.py > /dev/null 2>&1
  node "$GATE" > "$OUT" 2>&1
  echo $?
}

check() {  # check <label> <expected exit> <expected regex>
  local label="$1" want_exit="$2" want="$3" got_exit
  got_exit="$(run_gate)"
  # THE NUMBERS ARE THE EVIDENCE, and the first version of this printed only the
  # verdict lines - so the log recorded that [D] went red and not that it went
  # red at (285s, 300s], which is the half that says WHICH clock the page was on.
  local line
  line="$(grep -E 'sequence:|page-inflight:|first news in|arrives in|was measured by|still says nothing' "$OUT" | head -8)"
  if [ "$got_exit" = "$want_exit" ] && grep -qE "$want" "$OUT"; then
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

echo "=== [A] control: the tree as committed ==="
check "both sequence claims hold" 0 'ok    sequence: a figure the run in flight published'

echo "=== [B] D1 reverted in nodeTense: the qualifier goes back on everything ==="
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = """          if (flight) {
            if (record.published_by && record.published_by === flight) {"""
new = """          if (flight) {
            if (false) {"""
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "the page calls the run's own figures the previous cycle's" 1 \
      'was measured by deploy-stage #64, the run the page is watching'
restore

echo "=== [C] the fold stops carrying published_by ==="
# A DIFFERENT MECHANISM WITH THE SAME SYMPTOM. nodeTense() is untouched and
# correct; the record simply cannot answer. This is the shape the original
# defect actually had - the id was in the document and thrown away in the fold -
# and a gate that only catches [B] would be reading the wrong half.
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = "                                     published_by: wroteIt ? String(wroteIt) : null };"
new = "                                     published_by: null };"
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "a record that cannot say who wrote it is caught too" 1 \
      'was measured by deploy-stage #64, the run the page is watching'
restore

echo "=== [D] D2 reverted: the idle interval is a constant again ==="
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = """        if (!state.rateRemaining || !state.rateReset) return live ? 90000 : 120000;"""
new = """        if (!live) return 300000;
        if (!state.rateRemaining || !state.rateReset) return 90000;"""
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "the first news arrives on the five-minute clock and is refused" 1 \
      "first word about the run arrives in \(285s, 300s\]"
restore

echo "=== [E] the mock stops exposing the rate budget across the origin ==="
# NOT A PAGE DEFECT - AN INSTRUMENT DEFECT, and the one this gate shipped with.
# Without the refusal it measures the page's fallback branch and reports a number
# production never produces. It must refuse (exit 2) rather than answer.
python3 - <<'PY'
p = "scripts/check-page-inflight.mjs"
s = open(p).read()
old = '          "access-control-expose-headers": "x-ratelimit-remaining, x-ratelimit-reset"\n'
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, ""))
PY
check "a page that could not read the budget is refused, not measured" 2 \
      'could not read the rate budget'
restore

echo "=== [F] the publish stops changing anything the page draws ==="
# THE SUBJECT THAT NEVER BECAME ONE. If the overlay were byte-identical to the
# layer, claim 4 would pass on a page that learned nothing - the mirror of a
# control that reproduces its defect. Modelled by pointing the overlay at the
# unpublished document.
python3 - <<'PY'
p = "scripts/check-page-inflight.mjs"
s = open(p).read()
old = 'const PUBLISHED = path.join(FIXTURE, "layer-published");'
new = 'const PUBLISHED = path.join(FIXTURE, "layer");'
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "a publish that moves nothing is refused before any sentence is judged" 2 \
      'layer-published says it was written by run|the whole point of this pass'
restore

echo "=== [G] control again, after every mutation was restored ==="
check "the control is green on both sides of the breaks" 0 \
      'ok    sequence: the page.s first word about a run'

printf 'break-page-inflight-sequence: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
