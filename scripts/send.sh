#!/usr/bin/env bash
# Move a file from this buffer into the repo on the devbox — in one command.
#
#   ./send.sh <local-file> <path-relative-to-repo-root> ["commit message"]
#
# Without a commit message: copies the file into place and shows git status.
#   You review, then commit on the devbox yourself.
# With a commit message: also adds, commits, pushes, and clears the local copy.
#
# Examples:
#   ./send.sh session-primer.md docs/session-primer.md
#   ./send.sh session-primer.md docs/session-primer.md "docs: refresh the primer"
#
# Files produced in a chat land in outbox/. A bare filename is looked up there
# FIRST, and the resolved path is printed, so it is never a guess.
#
# If a bare name matches in BOTH the buffer root and outbox/, this script
# REFUSES. That case is not hypothetical: session-primer.md exists in both by
# design, and the old current-directory-first lookup silently delivered the
# stale attach-copy. The delivery then produced an empty diff, found nothing to
# commit, and died under `set -e` before printing "pushed" — a failure that
# looked almost like a success (ADR-0028).
#
# This file lives in the repository; the copy on the MacBook is a COPY.
#   scp devbox:aws-devops-sdet-demo/scripts/send.sh ~/Projects/_claude-transfer/

set -euo pipefail

DEVBOX="${DEVBOX:-devbox}"
REPO="${REPO:-aws-devops-sdet-demo}"   # relative to $HOME on the devbox

usage() {
  echo "usage: $0 <local-file> <path-relative-to-repo-root> [\"commit message\"]" >&2
  exit 1
}

[ $# -ge 2 ] && [ $# -le 3 ] || usage

LOCAL="$1"
DEST="$2"
MSG="${3:-}"

# Payload lives in outbox/. Accept either "outbox/foo.md" or a bare "foo.md".
# An explicit path is used exactly as given; only a BARE NAME is looked up.
case "$LOCAL" in
  */*) : ;;
  *)
    if [ -f "$LOCAL" ] && [ -f "outbox/$LOCAL" ]; then
      echo "ambiguous: $LOCAL exists in BOTH the buffer root and outbox/." >&2
      echo "Refusing to choose — the wrong one is the stale copy. Pass the path:" >&2
      echo "  $0 outbox/$LOCAL $DEST${MSG:+ \"$MSG\"}" >&2
      exit 1
    fi
    # An explicit `if`, not `[ -f ... ] && LOCAL=...`: under `set -e` the short
    # form survives only because a failing test in an AND list is exempt, and a
    # correctness that depends on that exemption is not one to build on.
    if [ -f "outbox/$LOCAL" ]; then
      LOCAL="outbox/$LOCAL"
    fi
    ;;
esac

[ -f "$LOCAL" ] || { echo "no such file: $LOCAL (looked in . and outbox/)" >&2; exit 1; }

case "$DEST" in
  /*|*..*) echo "dest must be a path inside the repo, e.g. docs/foo.md" >&2; exit 1 ;;
esac

BASE="$(basename "$LOCAL")"

# Print what was RESOLVED, not what was typed: a lookup whose result is invisible
# is how the stale copy got delivered in the first place.
echo "→ $LOCAL  →  $DEVBOX:~/$REPO/$DEST"
scp -q "$LOCAL" "$DEVBOX:/tmp/$BASE"

# ssh flattens its arguments into ONE string that the remote shell re-splits,
# so every argument must be pre-quoted for that shell. Without printf %q a
# commit message containing spaces arrives as several arguments and only the
# first word survives.
ARGS="$(printf '%q ' "$REPO" "$DEST" "$BASE" "$MSG")"

ssh "$DEVBOX" "bash -s -- $ARGS" <<'REMOTE'
set -euo pipefail
REPO="$1"; DEST="$2"; BASE="$3"; MSG="${4:-}"

cd "$HOME/$REPO"
git pull --quiet --ff-only
mkdir -p "$(dirname "$DEST")"
mv "/tmp/$BASE" "$DEST"

echo
echo "--- git status ---"
git status --short

if [ -z "$MSG" ]; then
  echo
  echo "Not committed (no message given). On the devbox:"
  echo "  cd ~/$REPO && git diff --stat && git add $DEST && git commit && git push"
  exit 0
fi

echo
echo "--- diff ---"
git add "$DEST"
git diff --cached --stat

git commit -q -m "$MSG"
git push -q
echo
echo "--- pushed ---"
git log --oneline -1
REMOTE

echo
if [ -n "$MSG" ]; then
  echo "committed and pushed. Local copy kept — you may still need it, e.g. to"
  echo "upload into the Claude Project. Delete it when done:"
else
  echo "delivered but NOT committed. Commit on the devbox, then delete:"
fi
echo "  rm $(pwd)/$LOCAL"
