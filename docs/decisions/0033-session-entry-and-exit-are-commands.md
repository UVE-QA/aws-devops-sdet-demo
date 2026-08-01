# ADR-0033: Session entry and exit are commands, not prose

## Status
Accepted (Ops, 2026-08-01).

## Context

Phase 16b was closed four times. Each time the session reported the exit
checklist complete, and each time something on it had not been done: the suite
list in three files, the teardown skill's idea of what an environment creates,
the "Current state" block of `docs/discussion-log.md` still saying the phase had
not started while the cursor said it was done, and a consequence ADR-0032
declared for `docs/demo-script.md` that nothing produced.

This was not a lack of instruction. The entry and exit rituals are written in
**four** places:

```text
CLAUDE.md                            "Start of every session" / "End of every session"
docs/session-primer.md               §A, §B, §C
.claude/skills/session-protocol      the full entry/exit checklist
.claude/skills/phase-gate            the closing ritual for a phase
```

The session read three of the four and missed six items anyway. **A fifth
document would be the defect, not the fix.** Prose does not run, and a session
that starts cold has no way to be reminded by a file it has not opened yet.

What has worked in this project, repeatedly, is a command that fails.

## Decision

Two commands, one at each end of a session. They do not replace the documents —
they execute the mechanical half of them, so the documents are left carrying
only what genuinely needs a human.

### `make session-open`

Refuses to start on a working copy that is not what it claims to be, then prints
the state a session would otherwise reconstruct from memory:

```text
REFUSES ON   a branch that is not main
             a dirty tree - starting on someone else's uncommitted work is how
             state gets lost
             local commits that were never pushed, i.e. a previous session that
             did not finish
PULLS        fast-forward only; a divergence is reported, never reconciled
             silently
PRINTS       the current phase, from the CURSOR rather than from anyone's
             memory; the newest session row; the newest ADR; and the three
             things a session must do before touching anything - STOP, report
             phase / next step / blockers, and rename the chat
```

### `make session-close`

Answers the questions the exit checklist asks, in the order it asks them:

```text
docs-check          delegated unchanged - it already runs in ci.yml
a summary exists    dated today OR yesterday, because sessions here cross
                    midnight UTC routinely and a gate that refuses over the
                    calendar gets skipped
INDEX <-> summaries both directions: an orphan summary and a dangling row are
                    both findings
INDEX is ORDERED    session-open reads the last row as the most recent one. A
                    row inserted in the wrong place makes the NEXT session
                    report the wrong state - which had already happened, in the
                    commit that closed 16b, and this check is what found it
the narrative       the `**As of YYYY-MM-DD.**` in docs/discussion-log.md must
                    equal the newest session's date
tree clean, pushed  work is only shared once pushed
ADR Consequences    printed, not verified
```

### Why the Consequences are printed rather than checked

A Consequences section is a TO-DO list written before the work, and nothing
re-reads it at the end. ADR-0032 said "the demo script and the architecture
document say what the line looks like" and only one of them was made to. No
reference check sees that: both files exist and both are valid. Printing it at
the one moment it is still actionable is the cheapest intervention that would
have caught it, and pretending to verify it would be a false guarantee.

### Why `session-close` is local only

On a CI checkout the working tree is always clean and HEAD always matches
origin, so "is everything committed" would be a check that cannot fail. This
project has found that shape at every layer; it is not going to build another
one deliberately.

## What this deliberately does not do

```text
- it cannot make anyone READ the output of session-open
- it does not check the transfer buffer: that lives on the MacBook, and this
  runs on the devbox
- it does not judge whether a summary is HONEST, only that it exists and is
  linked
- it does not touch docs-check, which stays exactly as it was
```

The claim is narrow on purpose: the mechanical half of the ritual now fails
loudly, so the human half has a smaller surface and a better chance.

## Consequences

- `scripts/session-open.sh` and `scripts/session-close.sh`, plus two Makefile
  targets.
- `CLAUDE.md`, `docs/session-primer.md` and `.claude/skills/session-protocol`
  lead with the command and keep only what it cannot do. Four descriptions of
  the ritual remain four, but three of them now defer to one runnable thing.
- Both commands must be broken on purpose before shipping, and were.
