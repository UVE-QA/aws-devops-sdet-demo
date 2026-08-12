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
# IT DERIVES ITS ANCHORS, AND THE FIRST VERSION DID NOT. Written during Phase 29,
# it named `28` and `2026-08-11` as literals - and scored 8 of 8, because Phase
# 29's own Current state block did not exist yet. The moment that block landed on
# top, every mutation went into a block BELOW the one the check reads, the check
# answered `phase 29` each time, and the devbox scored it 2 of 8. It failed
# loudly, which is the good outcome; what it was not is RE-RUNNABLE, and being
# re-runnable in a later session is the entire reason a break script is committed
# rather than typed. Third time in one phase that an instrument was pointed at
# the wrong part of the right thing.
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

OUT="$(mktemp -d)/session-close.out"
SHIM="$(mktemp -d)"
printf '#!/bin/sh\nexit 0\n' > "$SHIM/make"
chmod +x "$SHIM/make"

# THE TWO FILES, AND THEIR CURRENT ANCHORS, READ RATHER THAN NAMED.
DOC=docs/discussion-log.md
IDX=docs/sessions/INDEX.md
NEWDATE="$(grep '^| 20' "$IDX" | tail -1 | awk -F'|' '{gsub(/ /,"",$2); print $2}')"
NEWPHASE="$(grep '^| 20' "$IDX" | tail -1 | awk -F'|' '{gsub(/ /,"",$3); print $3}')"
PREVPHASE="$(grep -o '\*\*As of [0-9-]\{10\} ([0-9][0-9a-z.]*' "$DOC" | sed -n '2s/.*(//p')"
STALE=2026-08-04
if [ -z "$NEWDATE" ] || [ -z "$NEWPHASE" ] || [ -z "$PREVPHASE" ]; then
  echo "break-narrative-phase: could not read the anchors out of $DOC and $IDX -"
  echo "  newest session $NEWDATE / phase $NEWPHASE, block below the newest: $PREVPHASE"
  exit 2
fi
if [ "$NEWPHASE" = "$PREVPHASE" ]; then
  echo "break-narrative-phase: the two newest blocks name the same phase, so [B] would"
  echo "  mutate one and be judged on the other."
  exit 2
fi
echo "anchors: newest session $NEWDATE phase $NEWPHASE; the block under it is phase $PREVPHASE"
echo ""

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
  git checkout -- "$DOC" "$IDX" 2>/dev/null
}

# Run the REAL script and return the narrative section's own lines. Written to a
# file and read from the file: `$?` after a pipe is the pipe's, and this
# repository has already spent a session on that once (Phase 15b, Checkov).
narrative_says() {
  PATH="$SHIM:$PATH" bash scripts/session-close.sh > "$OUT" 2>&1
  # `^??` drops git's untracked listing from the dirty-tree check further down,
  # which names this very script and would otherwise appear under every variant.
  grep -E "$NARRATIVE" "$OUT" | grep -v '^===' | grep -v '^??' | sed 's/^/        /'
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
      "narrative $NEWDATE \($NEWPHASE\), matching the newest session"

echo "=== [B] THE DEFECT ITSELF: the newest block deleted, the one under it on top ==="
# Exactly the state main was in on 2026-08-11: the newest block is the PREVIOUS
# phase's, carrying the same date as the newest session, which is the whole
# reason the date said nothing. The date is forced to match rather than assumed
# to - two consecutive phases often close on the same day here, and when they do
# not, only the phase can speak.
python3 - "$NEWDATE" <<'PY2'
import re, sys
newdate = sys.argv[1]
p = "docs/discussion-log.md"
s = open(p).read()
hits = [m.start() for m in re.finditer(r'^\*\*As of \d{4}-\d{2}-\d{2} \(', s, re.M)]
assert len(hits) >= 2, "fewer than two Current state blocks; [B] would prove nothing"
s = s[:hits[0]] + s[hits[1]:]
s = re.sub(r'^\*\*As of \d{4}-\d{2}-\d{2} \(', '**As of %s (' % newdate, s, count=1, flags=re.M)
open(p, "w").write(s)
PY2
check "a block about the previous phase, on the same date, is refused" \
      "newest block is about phase $PREVPHASE and the newest"
restore

echo "=== [C] the block is present, dated right, and names no phase ==="
python3 - <<'PY2'
import re
p = "docs/discussion-log.md"
s = open(p).read()
s = re.sub(r'^\*\*As of (\d{4}-\d{2}-\d{2}) \([^)]*\)\.\*\*', r'**As of \1.**', s, count=1, flags=re.M)
open(p, "w").write(s)
PY2
check "a block with no parenthesis is refused, not silently accepted" \
      'names no phase'
restore

echo "=== [D] the INDEX row's phase column emptied ==="
python3 - <<'PY2'
p = "docs/sessions/INDEX.md"
lines = open(p).read().split("\n")
for k in range(len(lines) - 1, -1, -1):
    if lines[k].startswith("| 20"):
        parts = lines[k].split("|")
        parts[2] = "  "
        lines[k] = "|".join(parts)
        break
open(p, "w").write("\n".join(lines))
PY2
check "an INDEX row with no phase is refused rather than compared to nothing" \
      'carries no phase in its second column'
restore

echo "=== [E] the date check survived the change ==="
# The new check must not have replaced the old one. Same phase, wrong date.
python3 - "$STALE" <<'PY2'
import re, sys
p = "docs/discussion-log.md"
s = open(p).read()
s = re.sub(r'^\*\*As of \d{4}-\d{2}-\d{2} \(', '**As of %s (' % sys.argv[1], s, count=1, flags=re.M)
open(p, "w").write(s)
PY2
check "a stale date is still refused, and refused as a date" \
      "says $STALE, the newest session is $NEWDATE"
restore

echo "=== [F] no Current state block at all ==="
sed -i 's/^\*\*As of /**Once upon a time /' "$DOC"
check "a file with no As-of line at all is refused" \
      "has no '\*\*As of YYYY-MM-DD"
restore

echo "=== [G] the title wraps onto the next line: STILL GREEN ==="
# Not a break - a positive control for the parser. Only the token after `(` is
# read, so a phase whose title runs long must not make the check go quiet. It
# went quiet in exactly this way once already, one layer up: the 2026-08-08 fix
# in session-close.sh is there because a pattern that demanded the whole shape
# stopped matching when the shape grew.
python3 - <<'PY2'
import re
p = "docs/discussion-log.md"
s = open(p).read()
m = re.search(r'^(\*\*As of \d{4}-\d{2}-\d{2} \(\S+ )(.*)$', s, re.M)
assert m, "no Current state block to wrap; this variant would prove nothing"
wrapped = m.group(1) + "\n" + m.group(2)
open(p, "w").write(s[:m.start()] + wrapped + s[m.end():])
PY2
check "a wrapped title still reads as the newest phase" \
      "narrative $NEWDATE \($NEWPHASE\), matching the newest session"
restore

echo "=== [H] control again, after every mutation was restored ==="
check "the control is green on both sides of the breaks" \
      "narrative $NEWDATE \($NEWPHASE\), matching the newest session"

printf 'break-narrative-phase: %d of %d variants behaved as written.\n' \
       "$pass" "$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
