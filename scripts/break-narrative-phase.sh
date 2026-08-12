#!/usr/bin/env bash
# BREAK TEST for session-close's narrative check (Phase 29).
#
# The subject is a CONVENTION shared by two files - the phase in the second
# column of docs/sessions/INDEX.md, and the phase in the parenthesis of the
# newest `**As of <date> (<phase> — <title>).**` block in
# docs/discussion-log.md. A schema, in other words, spread across two documents
# that nothing else compares. Phase 27 committed its break script for the same
# reason: the next change to a schema owes the same proof, and a proof typed
# into a session is a proof nobody can re-run.
#
#     bash scripts/break-narrative-phase.sh
#
# WHAT THIS MEASURES, AND WHAT IT DELIBERATELY DOES NOT. session-close.sh sets
# one global `fail` for every check in it, and two of those checks - a clean
# tree and HEAD == origin/main - cannot pass in a sandbox that is mid-session by
# construction. So the script's EXIT STATUS is confounded here and is not the
# reading. The reading is the narrative section's own line, matched against what
# each variant is supposed to provoke. The unconfounded run is `make
# session-close` on the devbox at the end of the session, and it is not a
# substitute for this: it can only ever show the control.
#
# `make -s gates` is stubbed out by a shim on PATH. It belongs to a different
# section of the script, it is slow, and several of its gates need a browser.
# Nothing between the stub and the narrative check is touched.

set -uo pipefail
cd "$(dirname "$0")/.."

LOG="$(mktemp -d)/session-close.out"
SHIM="$(mktemp -d)"
printf '#!/bin/sh\nexit 0\n' > "$SHIM/make"
chmod +x "$SHIM/make"

# WHAT COUNTS AS THE NARRATIVE SECTION'S OWN OUTPUT. This list was written from
# the wording of the check's messages, and it was WRONG on the first run: [E]'s
# first line - `docs/discussion-log.md says <date>, the newest session is
# <date>` - contains none of `narrative`, `As of` or `newest block`, so the
# variant printed only the sentence underneath it and this harness scored a
# working refusal as a failure. The gate was blameless. Recorded rather than
# quietly widened, because it is the same shape as the thing being tested: an
# instrument that reads part of the right line, and a reading that is
# indistinguishable from a real defect until you look at what was filtered out.
NARRATIVE='narrative|Current state|As of|newest block|second column|discussion-log'
pass=0
fail=0

restore() {
  git checkout -- docs/discussion-log.md docs/sessions/INDEX.md 2>/dev/null
}

# Run the REAL script and return the narrative section's own lines. Written to a
# file and read from the file: `$?` after a pipe is the pipe's, and this
# repository has already spent a session on that once (Phase 15b, Checkov).
narrative_says() {
  PATH="$SHIM:$PATH" bash scripts/session-close.sh > "$LOG" 2>&1
  # `^??` drops git's untracked listing from the dirty-tree check further down,
  # which names this very script and would otherwise appear under every variant.
  grep -E "$NARRATIVE" "$LOG" | grep -v '^===' | grep -v '^??' | sed 's/^/        /'
}

check() {  # check <label> <expected-regex>
  local label="$1" want="$2" got
  got="$(narrative_says)"
  if printf '%s\n' "$got" | grep -qE "$want"; then
    printf 'ok    %s\n' "$label"
    pass=$((pass + 1))
  else
    printf 'FAIL  %s\n' "$label"
    printf '      expected to match: %s\n' "$want"
    fail=$((fail + 1))
  fi
  printf '%s\n' "$got"
  printf '\n'
}

trap restore EXIT

echo "=== [A] control: the tree as committed ==="
check "the narrative names the newest phase and the check says which" \
      'narrative 2026-08-11 \(28\), matching the newest session'

echo "=== [B] THE DEFECT ITSELF: the Phase 28 block deleted, 27 back on top ==="
# Exactly the state main was in between 2026-08-11 and this phase: the newest
# block is the previous phase's, and it carries the SAME DATE, which is the
# whole reason the date said nothing.
python3 - <<'PY'
import re
p = "docs/discussion-log.md"
s = open(p).read()
i = s.index("**As of 2026-08-11 (28")
j = s.index("**As of 2026-08-11 (27")
open(p, "w").write(s[:i] + s[j:])
PY
check "a block about the previous phase, on the same date, is refused" \
      'newest block is about phase 27 and the newest'
restore

echo "=== [C] the block is present, dated right, and names no phase ==="
sed -i '0,/\*\*As of 2026-08-11 (28 [^)]*)\.\*\*/s//**As of 2026-08-11.**/' docs/discussion-log.md
check "a block with no parenthesis is refused, not silently accepted" \
      'names no phase'
restore

echo "=== [D] the INDEX row's phase column emptied ==="
python3 - <<'PY'
p = "docs/sessions/INDEX.md"
lines = open(p).read().split("\n")
for k in range(len(lines) - 1, -1, -1):
    if lines[k].startswith("| 20"):
        parts = lines[k].split("|")
        parts[2] = "  "
        lines[k] = "|".join(parts)
        break
open(p, "w").write("\n".join(lines))
PY
check "an INDEX row with no phase is refused rather than compared to nothing" \
      'carries no phase in its second column'
restore

echo "=== [E] the date check survived the change ==="
# The new check must not have replaced the old one. Same phase, wrong date.
sed -i '0,/\*\*As of 2026-08-11 (28 /s//**As of 2026-08-04 (28 /' docs/discussion-log.md
check "a stale date is still refused, and refused as a date" \
      'says 2026-08-04, the newest session is 2026-08-11'
restore

echo "=== [F] no Current state block at all ==="
sed -i 's/^\*\*As of /**Once upon a time /' docs/discussion-log.md
check "a file with no As-of line at all is refused" \
      "has no '\*\*As of YYYY-MM-DD"
restore

echo "=== [G] the title wraps onto the next line: STILL GREEN ==="
# Not a break - a positive control for the parser. Only the token after `(` is
# read, so a phase whose title runs long must not make this check go quiet. It
# went quiet in exactly this way once already, one layer up: the 2026-08-08 fix
# in session-close.sh is there because a pattern that demanded the whole shape
# stopped matching when the shape grew.
python3 - <<'PY'
p = "docs/discussion-log.md"
s = open(p).read()
old = "**As of 2026-08-11 (28 — the cycle on a different day).**"
new = ("**As of 2026-08-11 (28 — the cycle on a different day, and two things\n"
       "nobody was looking for).**")
assert old in s, "the control's own anchor is gone; this variant proves nothing"
open(p, "w").write(s.replace(old, new, 1))
PY
check "a wrapped title still reads as phase 28" \
      'narrative 2026-08-11 \(28\), matching the newest session'
restore

echo "=== [H] control again, after every mutation was restored ==="
check "the control is green on both sides of the breaks" \
      'narrative 2026-08-11 \(28\), matching the newest session'

printf 'break-narrative-phase: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
