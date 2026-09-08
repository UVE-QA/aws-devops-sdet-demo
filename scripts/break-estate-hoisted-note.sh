#!/usr/bin/env bash
# BREAK TEST for the hoist half of page-inflight-check (Phase 39, ADR-0075).
#
# claimFiguresDated() used to read one place: the `.nstate` line on the node. The
# estate board says a sentence every tile of a row would print ONCE, on the row's
# header, so the claim now reads the union of the two - and a claim that reads
# more places is a claim that can be satisfied by more pages. This exists to show
# it is not satisfied by a page that says the sentence NOWHERE.
#
#     bash scripts/break-estate-hoisted-note.sh
#
# Two variants, because the hoist has two ways to lose the sentence and only one
# of them existed before it:
#
#   [B] the sentence is never produced      - the defect the claim was written for
#   [C] the sentence is produced, hoisted off every tile, and the header that
#       was supposed to carry it draws nothing - the defect the hoist ADDS, and
#       the one a per-node reading would have caught for free
#
# The tree must be clean: every variant patches assets/index.template.html and
# restores it with `git checkout`, which discards anything uncommitted in it.
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
  echo "break-estate-hoisted-note: $TPL or $GATE is dirty. Commit first - every"
  echo "variant below restores them with git checkout, which would take your edit with it."
  exit 2
fi

restore() {
  git checkout -- "$TPL" "$GATE" 2>/dev/null
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
  line="$(grep -E 'says which cycle|page-inflight:|does not say so|calls its figure' "$OUT" | head -6)"
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
check "the claim holds with the sentence on the row header" 0 \
      'ok    in-flight: a figure printed while a cycle is in flight says which cycle'

echo "=== [B] nodeTense stops producing the sentence at all ==="
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = """            return { word: "measured", note: "these figures are from the cycle before this one",
                     cls: "unobserved", gone: false };"""
new = """            return { word: "measured", note: "",
                     cls: "unobserved", gone: false };"""
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "a figure with no qualifier anywhere is caught" 1 \
      'prints a figure from the cycle before this one and does not say so'
restore

echo "=== [C] the hoist takes it off every tile and the header draws nothing ==="
# THE DEFECT THE HOIST ADDS. nodeTense() is untouched and correct, every tile
# correctly declines to repeat a sentence the row shares - and the row never
# says it. The page is then silent about a stale figure while every function
# involved is behaving as written, which is the shape this whole file exists for.
python3 - <<'PY'
p = "assets/index.template.html"
s = open(p).read()
old = """            if (sharedNote) hdr.insertAdjacentHTML("beforeend", `<span class="sharednote">${esc(sharedNote)}</span>`);"""
new = """            if (false) hdr.insertAdjacentHTML("beforeend", `<span class="sharednote">${esc(sharedNote)}</span>`);"""
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new))
PY
check "a sentence hoisted onto a header that never draws it is caught" 1 \
      'prints a figure from the cycle before this one and does not say so'
restore

echo "=== [D] control again, after every mutation was restored ==="
check "the control is green on both sides of the breaks" 0 \
      'ok    at-rest: a figure printed while a cycle is in flight says which cycle'

printf 'break-estate-hoisted-note: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
