#!/usr/bin/env bash
# THE CONTRAST GATE, BROKEN ON PURPOSE - once per refusal, plus a real floor
# failure, with a control green either side (Phase 27, ADR-0061).
#
# It is committed rather than typed into a session because the thing it tests is
# a SCHEMA. `chain` became `chains` in Phase 27 and every refusal had to be
# fired again on the new shape; the next change to that shape will owe the same
# proof, and a break test nobody can re-run is a break test nobody re-runs.
#
# A gate that has only ever been seen GREEN is indistinguishable from a gate
# that cannot fail. Each case below edits a tracked file, runs the gate, records
# the status STRAIGHT AFTER A REDIRECT - never through a pipe, which measures
# the pipe - and puts the file back.
#
#     bash scripts/break-contrast-chains.sh 2>&1 | tee /tmp/break-27.log
#
# CHROMIUM_PATH= on a machine whose chromium is not the pinned build, as for
# check-contrast.mjs itself.
set -u
cd "$(dirname "$0")/.."

CONTRACT=assets/contrast-contract.json
PAGE=site/index.html
GATE="node scripts/check-contrast.mjs"

# COMMIT BEFORE BREAKING THINGS ON PURPOSE. On 2026-07-28 a completed edit was
# lost to a `git checkout` after a deliberate break, silently. This refuses
# instead of taking that risk on someone's behalf.
if ! git diff --quiet -- "$CONTRACT" "$PAGE"; then
  echo "REFUSED: $CONTRACT or $PAGE has uncommitted changes."
  echo "  This script restores them with 'git checkout --', which would discard that work."
  exit 2
fi

echo "=== phase 27 - the contrast gate's refusals, on the new schema"
echo "host: $(uname -n)   commit: $(git rev-parse --short HEAD)   chromium: $(ls ~/.cache/ms-playwright 2>/dev/null | tr '\n' ' ')"
echo "exit codes are taken inside this script, straight after a redirect"
echo

run() {                      # run <label> <tail-lines>
  $GATE > /tmp/bc.out 2>&1
  echo "exit=$?"
  tail -"$2" /tmp/bc.out
  echo
}

edit() { python3 - "$CONTRACT" "$@"; }

echo "[0] control - the contract as committed"
run control 3

echo "[1] a probe that asks the chain for something that is not a colour"
edit <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for s in d["states"]:
    if s["id"] == "done": s["probe"]["property"] = "border-image-source"
json.dump(d, open(p, "w"), indent=2)
PY
run probe 3
git checkout -- "$CONTRACT"

echo "[2] the OLD key: chain instead of chains"
edit <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["chain"] = d.pop("chains")[0]["nodes"]
json.dump(d, open(p, "w"), indent=2)
PY
run oldkey 4
git checkout -- "$CONTRACT"

echo "[3] chains present and empty"
edit <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["chains"] = []
json.dump(d, open(p, "w"), indent=2)
PY
run empty 2
git checkout -- "$CONTRACT"

echo "[4] the same chain id twice"
edit <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["chains"].append(dict(d["chains"][0]))
json.dump(d, open(p, "w"), indent=2)
PY
run duplicate 2
git checkout -- "$CONTRACT"

echo "[5] a chain that declares no nodes"
edit <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["chains"][1]["nodes"] = []
json.dump(d, open(p, "w"), indent=2)
PY
run nonodes 3
git checkout -- "$CONTRACT"

echo "[6] a real floor failure - one state's edge lowered in the built page"
printf '<style>.node.done::before{background-color:#f4f4f6}</style>' >> "$PAGE"
run floor 9
git checkout -- "$PAGE"

echo "[7] control again - the same table, so every restore was clean"
run control 3

echo "tree after:"; git status --short; echo "(empty = every break was undone)"
