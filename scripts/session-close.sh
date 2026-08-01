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

say "=== the repository describes things that exist ==="
python3 scripts/check-docs-references.py || fail=1

say ""
say "=== the record of this session exists and agrees with itself ==="

today="$(date -u +%Y-%m-%d)"
yesterday="$(date -u -d 'yesterday' +%Y-%m-%d)"
# Today OR yesterday: sessions here run for hours and cross midnight UTC
# routinely. A gate that refuses at 00:30 over the calendar gets skipped.
summary="$(ls docs/sessions/"$today"-*.md docs/sessions/"$yesterday"-*.md 2>/dev/null | tail -1)"
if [ -z "$summary" ]; then
  bad "no session summary dated $today or $yesterday in docs/sessions/"
else
  say "summary   $summary"
fi

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

newest="$(printf '%s\n' "$dates" | sort | tail -1)"
stated="$(grep -o '\*\*As of [0-9-]*\.\*\*' docs/discussion-log.md | grep -o '[0-9-]\{10\}' | head -1)"
if [ -z "$stated" ]; then
  bad "docs/discussion-log.md has no '**As of YYYY-MM-DD.**' in Current state"
elif [ "$stated" != "$newest" ]; then
  bad "docs/discussion-log.md says $stated, the newest session is $newest -"
  bad "the narrative is behind the cursor, which is how Phase 16b closed"
else
  say "narrative $stated, matching the newest session"
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

previous="$(git ls-files docs/sessions | grep -v INDEX | sort | tail -2 | head -1)"
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
