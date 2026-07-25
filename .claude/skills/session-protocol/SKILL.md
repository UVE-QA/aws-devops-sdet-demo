---
name: session-protocol
description: >
  Use at the START and END of every working session on this repo, and whenever
  the user says "let's start", "where were we", "wrap up", "save progress",
  "commit what we did", "начнём", "на чём остановились", "заканчиваем",
  "сохрани прогресс". Covers pulling the latest source of truth, reading the
  phase cursor and ADRs, and on exit committing a session summary + pushing so
  work done on the devbox becomes visible from other machines. This is the
  glue that prevents lost context across sessions and machines.
  Do NOT use for: doing the actual phase work (use the operational skills),
  or for closing a phase gate specifically (see phase-gate, which this calls).
---

# Session Protocol

Context is kept in layers so sessions stay cheap on tokens: ADRs (rarely
change, always read), the phase cursor (where we are), and session summaries
(read on demand). Never paste full history into a session — read these files.

## On session entry

1. `git pull` — get the current source of truth before touching anything.
2. Read `docs/phase-gates.md` — current phase, last validated step, next allowed action.
3. Skim `docs/decisions/` — the "why" behind the architecture. Cheap to read.
4. Read `docs/sessions/INDEX.md` only if you need a specific past session;
   then open just that one file, not all of them.
5. Confirm working copy is on the devbox and on the expected branch.

State your understanding back in one or two lines ("We are in Phase 4, state
bucket bootstrapped, next is the network module") before doing work.

## During the session

- Keep the operation scoped to the current phase. Do not advance phases here.
- State (infra) lives in S3 + `terraform plan`, not in your memory. Read it,
  don't reconstruct it from conversation.
- Reach for `git diff` / `git log` instead of re-explaining code changes.

## On session exit

1. Run the validation relevant to what you did (the operational skill says which).
2. If the phase status changed, update `docs/phase-gates.md`.
3. Write a session summary to `docs/sessions/YYYY-MM-DD-<short-topic>.md`
   using the template below.
4. Add one row to `docs/sessions/INDEX.md`.
5. New architectural decisions → an ADR in `docs/decisions/`.
6. `git add` + `git commit` + `git push`. Until pushed, the work is only on
   the devbox and invisible from other machines.

## Session summary template

Keep it a summary, not a transcript. Transcripts stay in Claude Code.

```markdown
# Session YYYY-MM-DD — <short topic>

- Phase: <n>
- Request: <what the user wanted, 1-2 lines>
- Changed: <files / dirs touched>
- Commands run: <key commands>
- Result: <what works now / decision made>
- Blockers: <none | description>
- Next step: <the single next action>
```

## INDEX.md row format

```markdown
| 2026-06-06 | Phase 4 | bootstrapped S3 state backend | sessions/2026-06-06-state.md |
```
