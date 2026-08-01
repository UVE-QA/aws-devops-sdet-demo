# 2026-08-01 — Ops: session entry and exit become commands

Not a phase. A response to how Phase 16b closed: four times, each time reported
complete, each time with something on the exit checklist not done.

The checklist was never missing. It exists in four places — `CLAUDE.md`,
`docs/session-primer.md`, `.claude/skills/session-protocol` and
`.claude/skills/phase-gate` — and the session read three of them and missed six
items anyway. **ADR-0033**: prose does not run, and a fifth document would have
been the defect rather than the fix.

## What was built

```text
make session-open    refuses on a dirty tree, an unpushed previous session or
                     the wrong branch; pulls fast-forward only; prints the
                     current phase FROM THE CURSOR, the newest session row and
                     the newest ADR, then the three things to do before
                     touching anything
make session-close   docs-check (delegated, unchanged), a summary dated today
                     or yesterday, INDEX <-> summaries in both directions,
                     INDEX in chronological ORDER, the narrative's date against
                     the newest session, a clean tree, a pushed HEAD, and the
                     Consequences of any ADR this session added
```

`CLAUDE.md`, the primer §A and §C, and the `session-protocol` skill now lead
with the command and keep only what it cannot do. `scripts/check-docs-references.py`
was not touched.

## The scope this session got wrong first

It was asked for session discipline and started building a documentation linter
— an owner file for the suite list, per-block completeness checks, the skills
brought into `docs-check`. Useful work, and the wrong work: it addressed one
SYMPTOM of the 16b misses (the same list living in five files) rather than the
question asked. It was discarded on the spot rather than shipped alongside.

The tell is worth keeping: the linter was chosen because it was easy to check
mechanically. **Easy to check is not the same as important**, and the half
actually asked for — session ENTRY — had not been started at all when the drift
was caught.

## Break tests

```text
session-open   not on main                          RED
               a dirty working tree                 RED
session-close  INDEX out of chronological order     RED
               the narrative behind the cursor      RED
               a row pointing at nothing            RED
               a dirty tree / an unpushed HEAD      RED
               no summary dated today               RED
```

## Two findings, both from running the new commands

**`session-open` reported the wrong session on its first run.** It reads the
last row of `INDEX.md` as the most recent one, and the row closing Phase 16b had
been inserted ABOVE the 16a row six hours earlier — the table was no longer
chronological, and nothing had noticed. The ordering check in `session-close`
exists because of it, and it is a real defect class: a next session would have
opened on a stale account of where the project stood.

**A documented trap, walked into while testing.** The `INDEX.md` ordering fix
was uncommitted when the ordering break test ran, and `git checkout` restored
the file to HEAD — discarding the fix. `docs/session-primer.md` has said "COMMIT
BEFORE BREAKING THINGS ON PURPOSE" since 2026-07-28. Reading a trap is not the
same as not falling into it, which is the argument for this whole session in one
line.

## What these commands deliberately do not do

```text
- they cannot make anyone READ session-open's output
- the transfer buffer is on the MacBook and invisible from the devbox
- "is the summary honest" is not checkable; "does it exist and is it linked" is
- docs-check is unchanged; the list-completeness idea is parked, not adopted
```

## Owed, found and not fixed here

`.claude/skills/deploy-stage` writes `scripts/seed.py` for a path INSIDE the
container. The primer already says such paths must be absolute (`/app/scripts/...`)
precisely so a repo-shaped path is not mistaken for one. Left for a session that
is about the skills, rather than widening this one again.
