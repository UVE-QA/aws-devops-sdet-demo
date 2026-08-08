#!/usr/bin/env bash
# Session entry, as a command (ADR-0033).
#
# The entry ritual is written in four places - CLAUDE.md, docs/session-primer.md,
# .claude/skills/session-protocol and .claude/skills/phase-gate - and prose does
# not run. This does: it refuses to start a session on a working copy that is
# not what it claims to be, and it prints the state a session would otherwise
# reconstruct from memory.
#
# It cannot make anyone READ the output. It can make the state impossible to
# miss and impossible to get wrong.
set -uo pipefail

cd "$(dirname "$0")/.."
fail=0
say() { printf '%s\n' "$*"; }
bad() { printf 'session-open: %s\n' "$*"; fail=1; }

say "=== the working copy is what it claims to be ==="

branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] && say "branch    main" || bad "branch is $branch, not main"

dirty="$(git status --porcelain)"
if [ -n "$dirty" ]; then
  bad "the working tree is not clean. A session that starts on someone else's"
  bad "uncommitted work is how state gets lost:"
  printf '%s\n' "$dirty"
else
  say "tree      clean"
fi

git fetch --quiet origin || bad "could not fetch origin"
behind="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo '?')"
ahead="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
if [ "$behind" != "0" ]; then
  say "pulling   $behind commit(s) behind origin/main"
  git pull --ff-only --quiet || bad "git pull --ff-only refused; reconcile by hand"
fi
[ "$ahead" = "0" ] || bad "$ahead local commit(s) are not pushed - from a previous session?"
say "head      $(git rev-parse --short HEAD)"

say ""
say "=== where the project is (the cursor, not anyone's memory) ==="
say ""
# THE LAST `- Next allowed step:` IN docs/phase-gates.md, and the section
# heading above it.
#
# This read used to be "the last data row of the status table", and that was
# wrong from the moment a phase was planned in more than one row: the last row
# is the FURTHEST-OUT phase, not the next one. Phase 20.0 added 20b.2, 20c and
# 20d in one go on 2026-08-08, and every session after it opened by announcing
# `20d - Cost, computed and reconciled (planned, blocked on 20b)` while the
# actual next step was 20b.2. Green, specific, and pointing at the wrong box -
# the same shape as a layout check that measured the document instead of the
# node.
#
# Reading the status column instead does not work either, in either direction:
# the FIRST row that is not done is phase 8, open and deliberately parked since
# July. The status column says how a phase ended, never which one is next.
#
# So this reads the line the document already writes for exactly this purpose.
# Every closing section ends with one, the newest section is last, and the
# session primer already tells a chat to name itself from it. Derived from the
# structure rather than duplicated into a field somebody has to remember to
# update - a second place claiming the current phase is how the first one goes
# stale.
# No interval quantifier. `/^#{2,3} /` was written here first and it is a
# portability trap: under the devbox's mawk 1.3.4 it matched `## Completion
# criteria & validation` and not one of the thirty-three `### Phase` headings,
# so the fix for a cursor pointing at the wrong row shipped pointing at a
# different wrong row. Plain `/^### /` is what a phase section is.
cursor="$(awk '
  /^### / { section = $0 }
  /^- Next allowed step:/ { s = section; step = $0; capture = 1; next }
  capture == 1 { if ($0 ~ /^  /) { step = step "\n" $0 } else { capture = 0 } }
  END {
    if (s == "") exit 1
    printf "%s\n%s\n", s, step
  }' docs/phase-gates.md)"

if [ -z "$cursor" ]; then
  bad "docs/phase-gates.md has no '- Next allowed step:' line. That line IS the"
  bad "cursor; without it nothing here knows what comes next."
else
  printf 'phase     %s\n' "$(printf '%s\n' "$cursor" | head -1 | sed 's/^#* *//')"
  printf '%s\n' "$cursor" | tail -n +2 | sed 's/^- Next allowed step: /next      /; s/^  /          /'
fi

say ""
say "plan      docs/next-phases.md - read it before proposing anything"
say ""
say "last session:"
grep -v '^| Date' docs/sessions/INDEX.md | grep '^|' | tail -1 \
  | awk -F'|' '{printf "  %s  %s\n", $2, substr($4,1,120)}'

say ""
newest_adr="$(ls docs/decisions/*.md | sort | tail -1)"
say "newest ADR: $(head -1 "$newest_adr")"

say ""
say "=== before you touch anything ==="
say "STOP. State the current phase, the next allowed step, and any blocker."
say "Wait for confirmation. Do not advance a phase without it."
say "Rename this chat: Phase <N> — <topic>, or Ops — <topic>."
say ""

if [ "$fail" -ne 0 ]; then
  say "session-open: NOT clean. Fix the above before starting work."
  exit 1
fi
say "session-open: ready."
