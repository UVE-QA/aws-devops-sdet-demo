#!/usr/bin/env bash
# Session exit, as a command (ADR-0033).
#
# The exit checklist exists in four documents. Phase 16b was closed four times,
# each time reported complete, and each time something on that list had not been
# done. Prose does not run; this does.
#
# Local only, deliberately. On a CI checkout the working tree is always clean
# and HEAD always matches, so "is everything committed" would be a check that
# cannot fail - the exact defect this project keeps finding one layer down.
#
# What it CANNOT see: the transfer buffer at ~/Projects/_claude-transfer/outbox.
# That lives on the MacBook and this runs on the devbox. Claiming otherwise
# would be worse than not checking it.
set -uo pipefail

cd "$(dirname "$0")/.."
fail=0
say() { printf '%s\n' "$*"; }
bad() { printf 'session-close: %s\n' "$*"; fail=1; }

say "=== every cheap gate, from the list ci.yml reads (ADR-0057) ==="
# THIS USED TO BE THREE CHECKS WHILE CI RAN TWELVE, and the gap was not
# theoretical: a session could print `session-close: clean` and redden main with
# the same commit, and one did, twice.
#
#   20i   docs/decisions gained ADR-0051, topology.json was generated BEFORE it
#         and never again. Green in the chat's sandbox, red on the devbox.
#         Fixed by 1d8980b.
#   21    the identical thing, two ADRs at once, 54 against 56. It reached main:
#         run 31343885958 went red while session-close printed `clean`.
#
# What makes it specific rather than careless: topology.json counts the files in
# docs/decisions/, so a DOCUMENTS-ONLY session - a session that deliberately
# touches no code, which is exactly what a decisions phase is - changes a
# generated number without going anywhere near the generator. Phase 22 added the
# two generated-artifact checks here and wrote down that the shape was still
# wrong; Phase 23 is that shape. One list, two readers, in assets/gates.json.
#
# `make gates` refuses before it runs anything if the list has lost a gate the
# repository still has, so the price of one list - that it can shrink in
# silence - is paid by scripts/run-gates.py rather than by the next session.
make -s gates || fail=1

say ""
say "=== the record of this session exists and agrees with itself ==="

tracked="$(git ls-files docs/sessions)"
index="docs/sessions/INDEX.md"

for f in $tracked; do
  case "$f" in */INDEX.md) continue;; esac
  grep -q "$(basename "$f")" "$index" || bad "$f exists but no row in INDEX points at it"
done

for linked in $(grep -o 'sessions/[A-Za-z0-9._-]*\.md' "$index" | sort -u); do
  [ -f "docs/$linked" ] || bad "INDEX points at $linked, which does not exist"
done

dates="$(grep '^| 20' "$index" | awk -F'|' '{gsub(/ /,"",$2); print $2}')"
if [ "$dates" != "$(printf '%s\n' "$dates" | sort)" ]; then
  bad "INDEX rows are not in chronological order - session-open reads the LAST"
  bad "row as the most recent one, and would report the wrong session"
fi

# WHICH SESSION IS THE NEWEST ONE IS A QUESTION WITH ONE ANSWER HERE, AND IT IS
# THE LAST ROW OF INDEX. This used to be `ls docs/sessions/<today>-*.md | tail
# -1`, which sorts alphabetically: on 2026-08-08 four summaries carried that
# date and it printed the LAYOUT PILOT while the newest was the generator
# session. Two sub-phases in one day is not unusual here - 20a took three - and
# the filenames are named after what a session established, so their alphabet
# says nothing about their order.
#
# INDEX is append-ordered and the check directly above refuses when it is not
# chronological, so reusing it means this script holds ONE ordering rather than
# two that can disagree. It also stops *.log evidence files being mistaken for
# summaries, which the old `git ls-files` form did further down.
row_file() {  # row_file <n from the end> -> the first sessions/*.md in that row
  grep '^| 20' "$index" | tail -"$1" | head -1 \
    | grep -o 'sessions/[A-Za-z0-9._-]*\.md' | head -1
}
row_date() {
  grep '^| 20' "$index" | tail -"$1" | head -1 | awk -F'|' '{gsub(/ /,"",$2); print $2}'
}
row_phase() {
  grep '^| 20' "$index" | tail -"$1" | head -1 | awk -F'|' '{gsub(/ /,"",$3); print $3}'
}

newest="$(row_date 1)"
summary="$(row_file 1)"
today="$(date -u +%Y-%m-%d)"
yesterday="$(date -u -d 'yesterday' +%Y-%m-%d)"
if [ -z "$summary" ]; then
  bad "the last row of $index names no sessions/<file>.md"
# Today OR yesterday: sessions here run for hours and cross midnight UTC
# routinely. A gate that refuses at 00:30 over the calendar gets skipped.
elif [ "$newest" != "$today" ] && [ "$newest" != "$yesterday" ]; then
  bad "the newest INDEX row is dated $newest, not $today or $yesterday -"
  bad "this session has not added one"
else
  say "summary   docs/$summary"
fi

# THE FIRST 'As of' LINE, WHATEVER FOLLOWS THE DATE. This used to require
# '**As of <date>.**' exactly, and every Current state block written since
# 2026-08-08 carries the phase in parentheses - '**As of 2026-08-08 (20f -
# ...).**' - which that pattern does not match. So the check fell through the
# whole file to line 514, an entry from an earlier phase, and read ITS date.
# It was GREEN on 2026-08-08 by coincidence: that stale line happens to say
# 2026-08-08, and so did the newest session that day. The coincidence ended on
# 2026-08-09 and that is the only reason it spoke. A gate reading the wrong
# line is indistinguishable from a gate reading the right one until the two
# answers differ.
#
# AND THE DATE ALONE WAS NOT ENOUGH. Phase 28 closed on 2026-08-11 without
# touching this file at all: the newest block was still Phase 27's, and 27 had
# closed the SAME DAY, so the dates matched and this printed `narrative
# 2026-08-11, matching the newest session`. Green on a block describing the
# wrong phase, and nothing else in the repository would ever have said so -
# docs-check does not read this file, and the next session reads the top of it
# for context. The recurring shape here, one layer up from the 2026-08-08 fix
# above: not a gate reading the wrong LINE, a gate reading too little of the
# right one. Several sessions a day is normal in this project, so the date can
# only ever be a weak identifier, and it happens to be strongest on exactly the
# days when the most is going on.
#
# The phase is the second column of the INDEX row and the parenthesis in the
# block's own first line, a convention every block since 2026-08-08 follows.
# Only the token immediately after `(` is read, so a long title may wrap onto
# the next line without this going quiet.
asof="$(grep -m1 '\*\*As of [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' docs/discussion-log.md)"
stated="$(printf '%s\n' "$asof" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' | head -1)"
stated_phase="$(printf '%s\n' "$asof" | sed -n 's/.*\*\*As of [0-9-]\{10\} (\([0-9][0-9a-z.]*\) .*/\1/p')"
newest_phase="$(row_phase 1)"
if [ -z "$stated" ]; then
  bad "docs/discussion-log.md has no '**As of YYYY-MM-DD.**' in Current state"
elif [ "$stated" != "$newest" ]; then
  bad "docs/discussion-log.md says $stated, the newest session is $newest -"
  bad "the narrative is behind the cursor, which is how Phase 16b closed"
elif [ -z "$newest_phase" ]; then
  bad "the last row of $index carries no phase in its second column, so the"
  bad "narrative cannot be checked against anything but a date"
elif [ -z "$stated_phase" ]; then
  bad "the newest Current state block names no phase: \"$asof\""
  bad "the convention since 2026-08-08 is '**As of <date> (<phase> — <title>).**'"
elif [ "$stated_phase" != "$newest_phase" ]; then
  bad "the narrative's newest block is about phase $stated_phase and the newest"
  bad "session is phase $newest_phase - both dated $stated, which is why the date"
  bad "alone said nothing. This is how Phase 28 closed with no block at all"
else
  say "narrative $stated ($stated_phase), matching the newest session"
fi

say ""
say "=== nothing is left only on this machine ==="

dirty="$(git status --porcelain)"
if [ -n "$dirty" ]; then
  bad "the working tree is not clean:"
  printf '%s\n' "$dirty"
else
  say "tree      clean"
fi

git fetch --quiet origin || bad "could not fetch origin"
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  bad "HEAD is not origin/main - work is only shared once pushed"
else
  say "pushed    $(git rev-parse --short HEAD)"
fi

say ""
say "=== Consequences of the ADRs this session added ==="
say "Not verified - re-read. A Consequences section is a TO-DO list written"
say "before the work, and ADR-0032 declared one for docs/demo-script.md that"
say "nothing produced until it was noticed by hand."
say ""

# The SAME assumption, one more time: this was `git ls-files docs/sessions |
# sort | tail -2 | head -1`, which is alphabetical and counts *.log evidence
# files as sessions. On 2026-08-08 it happened to land on the right file, which
# is the worst kind of green. Second-to-last INDEX row instead.
previous="docs/$(row_file 2)"
base="$(git log -1 --format=%H --diff-filter=A -- "$previous" 2>/dev/null)"
if [ -z "$base" ]; then
  say "could not locate the previous session's commit; skipping"
else
  adrs="$(git log --diff-filter=A --name-only --format= "$base"..HEAD -- docs/decisions/ | sort -u)"
  if [ -z "$adrs" ]; then
    say "no ADR added since $previous"
  else
    for adr in $adrs; do
      [ -f "$adr" ] || continue
      say "--- $adr"
      awk '/^## Consequences/{p=1;next} /^## /{p=0} p' "$adr"
    done
  fi
fi

say ""
if [ "$fail" -ne 0 ]; then
  say "session-close: NOT clean. The session is not over."
  exit 1
fi
say "session-close: clean. Refresh the primer copy on the Mac if it changed,"
say "and leave ~/Projects/_claude-transfer/outbox empty."
