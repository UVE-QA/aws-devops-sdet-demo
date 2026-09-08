#!/usr/bin/env bash
# BREAK TEST for the partial-reading claim of page-inflight-check (Phase 39,
# ADR-0076).
#
#     bash scripts/break-progress-attribution.sh
#
# The claim is two-sided and both sides are the point:
#
#   [B] the page stops reading the document at all - the vacuous green this file
#       has caught in itself twice, where every other claim about the reading
#       stays true because there is no reading
#   [C] the page reads a document with no run in flight at all - a reading left
#       behind by a finished cycle then lights an environment that has been torn
#       down since, which is the twelve minutes prod.rds spent at full colour
#       while it was being deleted
#   [D] the document names a DIFFERENT run from the one in flight. The page must
#       refuse it, and the observable consequence is that the gate goes red for
#       the OTHER half of the same claim - nothing was painted. [D2] then removes
#       the comparison and the gate goes green again over the same fixture, which
#       is what shows the comparison did it rather than something else
#   [E] the document has gone stale - nobody is writing it any more. On
#       2026-09-08 this was the ONLY defence left: prod's apply errored so no
#       record was published to supersede it, and the removal was denied because
#       the stop step held the wrong role
#   [F] the record stops superseding the partial reading - the board goes on
#       saying `being created` over an environment the same run has already
#       reported complete
#
# The tree must be clean: every variant patches assets/index.template.html or
# the layer fixture and restores them with `git checkout`, which discards
# anything uncommitted in them.

set -uo pipefail
cd "$(dirname "$0")/.."

TPL="assets/index.template.html"
GATE="scripts/check-page-inflight.mjs"
DOC="tests/fixtures/page-inflight/layer/status/progress/stage.json"
OUT="$(mktemp -d)/gate.out"
pass=0
fail=0

if [ -n "$(git status --porcelain -- "$TPL" "$GATE" "$DOC")" ]; then
  echo "break-progress-attribution: $TPL or $GATE is dirty. Commit first - every"
  echo "variant below restores them with git checkout, which would take your edit with it."
  exit 2
fi

restore() {
  git checkout -- "$TPL" "$GATE" "$DOC" 2>/dev/null
  python3 scripts/build-site-page.py > /dev/null 2>&1
}
trap restore EXIT

run_gate() {
  python3 scripts/build-site-page.py > /dev/null 2>&1
  node "$GATE" > "$OUT" 2>&1
  echo $?
}

check() {  # check <label> <expected exit> <expected regex>
  local label="$1" want_exit="$2" want="$3" got_exit line
  got_exit="$(run_gate)"
  line="$(grep -E 'partial reading|page-inflight:|were painted|no node on the page|says anything different' "$OUT" | head -6)"
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
check "the claim holds in both states" 0 \
      'ok    in-flight: a partial reading is read only by the run that wrote it'

echo "=== [B] the page stops reading the document ==="
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = "          if (!doc || doc.partial !== true) return null;"
new = "          if (true) return null;"
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "a page that never reads it is caught, not green" 1 \
      'no node on the page was painted from status/progress'
restore

echo "=== [C] the page reads a partial document with no run in flight ==="
# ALL THREE GUARDS COME OUT, and that is a finding rather than a heavier hand.
# At rest the flight guard refuses because `flightHere()` answers null; the
# run-id comparison refuses independently, because a document naming a run can
# never equal null; and the shelf life refuses independently again, because this
# fixture's clock is thirteen minutes past the document. Removing any one leaves
# the case defended - which is why the first version of this variant passed with
# the comparison gone and proved nothing. What the claim has to be shown catching
# is the STATE, so the variant produces the state.
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
pairs = [
    ("          if (!flight || flight === true) return null;", "          if (false) return null;"),
    ("          if (!wroteIt || String(wroteIt) !== flight) return null;", "          if (false) return null;"),
    ("          if (!taken || Date.now() - taken > PROGRESS_SHELF_MS) return null;", "          if (false) return null;"),
]
for old, new in pairs:
    assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
    s = s.replace(old, new)
open(p, "w").write(s)
PY
check "a reading left behind by a finished cycle is caught at rest" 1 \
      'were painted from a partial reading with no run in flight'
restore

echo "=== [D] the document names a run that is NOT the one in flight ==="
# THE FIXTURE MOVES HERE, NOT THE PAGE. With the page as committed this must
# produce a board that paints nothing - and `nothing painted while a run is in
# flight` is the other half of the same claim, so the gate goes red saying so.
python3 - <<'PY'
import json
p = "tests/fixtures/page-inflight/layer/status/progress/stage.json"
d = json.load(open(p))
assert d["run"]["id"] == "31461000064", "the fixture moved; this variant would prove nothing"
d["run"] = {"id": "31461000099", "number": "99", "workflow": "deploy-stage"}
json.dump(d, open(p, "w"), indent=2)
PY
check "a document naming another run is refused by the page" 1 \
      'no node on the page was painted from status/progress'

echo "=== [D2] ... and the comparison is what refused it ==="
# Same fixture, still naming #99. Removing the comparison makes the page accept
# it, the board paints, and the gate goes GREEN over a page reading a document
# written by a different cycle. Green is the DEFECT here, and it is the contrast
# with [D] that shows which line was doing the work.
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = "          if (!wroteIt || String(wroteIt) !== flight) return null;"
new = "          if (false) return null;"
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "without it the page accepts the other run's document" 0 \
      'ok    in-flight: a partial reading is read only by the run that wrote it'
restore

echo "=== [E] the document is old, so nobody is writing it any more ==="
# THE LAST DEFENCE, AND ON 2026-09-08 THE ONLY ONE LEFT. prod's apply timed out
# waiting for an ALB, so no record was published to supersede the document, and
# the removal was denied because the stop step held the wrong role. Both other
# defences gone at once. This one is a fact the DOCUMENT carries, so it holds
# when the bucket, the workflow and the credential have all failed together.
python3 - <<'PY'
import json
p = "tests/fixtures/page-inflight/layer/status/progress/stage.json"
d = json.load(open(p))
assert d["taken_at"] == "2026-08-11T04:11:46Z", "the fixture moved; this variant would prove nothing"
d["taken_at"] = "2026-08-11T03:55:00Z"      # seventeen minutes before the fixture's clock
json.dump(d, open(p, "w"), indent=2)
PY
check "a reading nobody has refreshed in seventeen minutes is dropped" 1 \
      'no node on the page was painted from status/progress'
restore

echo "=== [F] the record stops superseding the partial reading ==="
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = """            n.progress = reported
              ? null
              : nodeProgress(n, progressHere(RUNSTATE.observation, n.env));"""
new = """            n.progress = nodeProgress(n, progressHere(RUNSTATE.observation, n.env));"""
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "a publish that the board ignores is caught by the sequence pass" 1 \
      'not one of the published nodes says anything different after the swap'
restore

echo "=== [G] control again, after every mutation was restored ==="
check "the control is green on both sides of the breaks" 0 \
      'ok    at-rest: a partial reading is read only by the run that wrote it'

printf 'break-progress-attribution: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
