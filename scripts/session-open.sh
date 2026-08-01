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
# The last data row of the status table in docs/phase-gates.md.
awk -F'|' '/^\| *[0-9]/ {phase=$2; title=$3; status=$4} END {
  printf "phase     %s -%s (%s)\n", gensub(/ /,"","g",phase), title, gensub(/^ +| +$/,"","g",status)
}' docs/phase-gates.md

say "next      docs/next-phases.md - read it before proposing anything"
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
