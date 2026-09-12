#!/usr/bin/env bash
# BREAK TEST for claim-chain (Phase 39, ADR-0085).
#
#     bash scripts/break-claim-chain.sh
#
# The gate compares three statements of one fact and passes when they agree.
# A check that passes is not evidence until it has been shown to fail, and this
# one has three separate ways to be vacuously green: a copy that moved, a copy
# that lost its chain entirely, and a copy that changed it. All three below.
#
# The template and the README are restored with `git checkout`, so both must be
# clean before this runs.

set -uo pipefail
cd "$(dirname "$0")/.."

TPL="assets/index.template.html"
RDM="README.md"
pass=0
fail=0

if [ -n "$(git status --porcelain -- "$TPL" "$RDM")" ]; then
  echo "break-claim-chain: $TPL or $RDM is dirty. Commit first - every variant"
  echo "restores them with git checkout, which would take your edit with it."
  exit 2
fi

restore() { git checkout -- "$TPL" "$RDM" 2>/dev/null; }
trap restore EXIT

check() {  # check <label> <expected exit> <expected substring>
  local label="$1" want_exit="$2" want="$3" out got
  out="$(python3 scripts/check-claim-chain.py 2>&1)"; got=$?
  if [ "$got" = "$want_exit" ] && printf '%s' "$out" | grep -qF "$want"; then
    printf 'ok    %s\n' "$label"
    pass=$((pass + 1))
  else
    printf 'FAIL  %s\n      wanted exit %s containing: %s\n' "$label" "$want_exit" "$want"
    fail=$((fail + 1))
  fi
  printf '%s\n\n' "$out" | sed 's/^/        /'
}

echo "=== [A] control: the tree as committed ==="
check "the three agree" 0 "all stating"

echo "=== [B] the README gains a step the page does not name ==="
python3 - <<'PY'
p = "README.md"; s = open(p).read()
old = "A deploy → test → promote → destroy pipeline"
new = "A deploy → test → promote → verify → destroy pipeline"
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new, 1))
PY
check "a chain that grew in one copy is caught" 1 "THE COPIES DISAGREE"
restore

# The step this drops is `promote`, not `approve`: ADR-0086 took `approve` out of
# the chain for good, and a variant removing a verb that is no longer there would
# assert nothing. The defect being reproduced is the same one - a copy shortened
# by a word - and the verb is whichever one is still in all three.
echo "=== [C] the row loses a step, which is the defect this was written for ==="
python3 - <<'PY'
p = "assets/index.template.html"; s = open(p).read()
old = '<span class="ident-what">deploy &rarr; test &rarr; promote &rarr; destroy on AWS'
new = '<span class="ident-what">deploy &rarr; test &rarr; destroy on AWS'
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new, 1))
PY
check "a chain that lost a step is caught" 1 "THE COPIES DISAGREE"
restore

echo "=== [D] a copy loses its chain entirely ==="
# THE EMPTY RESULT THAT LOOKS CLEAN. With no chain to compare, a checker that
# only compared what it found would report agreement between the two that
# remain - which is the failure mode this repository keeps finding in itself.
python3 - <<'PY'
p = "assets/index.template.html"; s = open(p).read()
old = 'deploy &rarr; test &rarr; promote &rarr; destroy on AWS, reporting on itself'
new = 'a pipeline on AWS, reporting on itself'
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new, 1))
PY
check "a copy with no chain at all is refused, not ignored" 1 "no arrow chain found"
restore

echo "=== [E] the markup the gate reads is renamed under it ==="
python3 - <<'PY'
p = "assets/index.template.html"; s = open(p).read()
old = '<span class="ident-what">'
new = '<span class="ident-says">'
assert s.count(old) == 1, "the anchor moved; this variant would prove nothing"
open(p, "w").write(s.replace(old, new, 1))
PY
check "a moved copy is refused, not silently dropped" 1 "could not find"
restore

echo "=== [F] control again, after every mutation was restored ==="
check "the three agree again" 0 "all stating"

printf 'break-claim-chain: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
