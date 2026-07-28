# ADR-0028: Control-layer tooling lives in the repository

## Status
Accepted (Phase 12). Closes the "Known debt" section that the transfer buffer's
own README had left open, deliberately, for an ADR.

## Context

`send.sh` and the buffer README existed **only on the MacBook**. They are how a
chat session's work reaches git at all, and they were outside git.

This is the same shape as the finding of 2026-07-25, when `CLAUDE.md` and the
nine skills turned out never to have been committed — Claude Code had been
starting with no anchor and no skills for seven weeks, while a document asserted
that GitHub was the source of truth. The assertion was made by a file that was
itself outside the source of truth.

The argument for leaving them out was not empty, and the buffer README stated it
plainly: moving them in recreates the two-copies problem, because `send.sh` has
to exist on the MacBook to run. That is real. But it is the same problem the
primer copy already has and already survives, and the two files differ in the
property that matters — **rate of change**. The primer went stale three times in
one session; `send.sh` has changed once since it was written.

Left outside git these files have no history, no review, and no way to be
repaired by anyone who does not have this laptop. A bug in `send.sh` was
diagnosed on 2026-07-26 and could not be fixed durably, because there was
nowhere to fix it.

## Decision

```text
scripts/send.sh            in git. The MacBook copy is a COPY.
docs/transfer-buffer.md    in git. Describes the buffer, the patch workflow,
                           and the one-off path.
```

The buffer keeps working exactly as before; what changes is which copy is
authoritative. The same sentence already governs `docs/session-primer.md`, and
the same refresh command works for both:

```text
scp devbox:aws-devops-sdet-demo/scripts/send.sh ~/Projects/_claude-transfer/
```

The bug this makes fixable is fixed in the same commit. `send.sh` resolved a
bare filename by checking the current directory first, so
`./send.sh session-primer.md ...` silently delivered the **stale attach-copy in
the buffer root** instead of the fresh one in `outbox/` — the one filename that
exists in both places by design. It now **refuses** when a bare name matches in
both, rather than choosing, and it prints the source path it resolved so the
choice is visible when it does choose.

Refusing rather than preferring `outbox/` is the point. Preferring would still
be a silent decision, and silence was the whole defect: on 2026-07-26 the
delivery produced an empty diff, `git commit` found nothing to commit, and
`set -e` ended the script before the word "pushed" — a failure that looked
almost like a success.

## Consequences

```text
easy      the tooling has a history, and can be fixed from anywhere. A future
          session can read send.sh from the clone instead of asking what it does.
costs     one more file to refresh on the MacBook after a push that touches it.
          Named in docs/transfer-buffer.md next to the primer's refresh command,
          because an unwritten refresh is how the primer went stale three times.
watch     the copies. If send.sh ever changes often enough to go stale the way
          the primer does, that is the signal to make the buffer a checkout
          rather than a folder of copies - which is a different ADR.
```

The rule this generalises, now stated for the third time in this project: **a
document that asserts where the source of truth is does not thereby put itself
there.** Check `git ls-files` before believing it.
